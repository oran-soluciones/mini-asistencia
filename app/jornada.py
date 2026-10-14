"""La jornada del día: una sola regla para la vista Hoy, la columna Tipo y el Excel.

Reglas (las mismas que documenta app/reports.py):
- Las marcaciones válidas de cada día van de a pares: 1.ª entrada, 2.ª salida, 3.ª entrada,
  4.ª salida... Cada día empieza de nuevo con una entrada. Horas = suma de los pares completos.
- Una marcación a menos de 2 minutos de la última válida es repetida y se ignora.
- Las anuladas a mano desde el panel no cuentan: las demás se reacomodan solas.
- Cantidad impar de válidas: sigue en el colegio (falta la última salida). Ninguna: sin marcar.
- No se cruza la medianoche: cada día calendario se analiza por separado.

Todo son funciones puras (el "ahora" se inyecta), así se testean sin base ni reloj.
"""
import unicodedata
from datetime import datetime, timedelta
from typing import NamedTuple

REPETIDA_MIN = timedelta(minutes=2)

ENTRADA, SALIDA, REPETIDA, ANULADA = "Entrada", "Salida", "Repetida", "Anulada"

EN_COLEGIO, SE_RETIRO, SIN_MARCAR = "en_colegio", "se_retiro", "sin_marcar"
ESTADOS = {EN_COLEGIO: "En el colegio", SE_RETIRO: "Se retiró", SIN_MARCAR: "Sin marcar"}

# Franja de "La jornada": de 07:00 a 19:00 (horario diurno)
INICIO_MIN = 7 * 60
FIN_MIN = 19 * 60
ESCALA_MIN = FIN_MIN - INICIO_MIN
MARCAS_HORA = list(range(7, 20))  # 07 08 09 … 19, chiquitas arriba de cada marquita de la franja

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


class Jornada(NamedTuple):
  momentos: list[datetime]  # todas las marcaciones, en orden
  tipos: list[str]          # tipo de cada una (mismo orden que `momentos`)
  validas: list[datetime]   # las que cuentan (sin repetidas)

  @property
  def entrada(self) -> datetime | None:
    """Primera entrada del día."""
    return self.validas[0] if self.validas else None

  @property
  def abierta(self) -> bool:
    """Cantidad impar de válidas: la última entrada todavía no tiene salida."""
    return len(self.validas) % 2 == 1

  @property
  def salida(self) -> datetime | None:
    """Última salida, solo si se retiró (cada entrada tiene su salida)."""
    return self.validas[-1] if self.validas and not self.abierta else None

  @property
  def pares(self) -> list[tuple[datetime, datetime | None]]:
    """(entrada, salida) en orden; la última salida es None si sigue en el colegio."""
    v = self.validas
    return [(v[i], v[i + 1] if i + 1 < len(v) else None) for i in range(0, len(v), 2)]

  @property
  def horas(self) -> timedelta:
    """Suma de los pares completos (el par abierto no suma)."""
    return sum((s - e for e, s in self.pares if s), timedelta(0))

  @property
  def repetidas(self) -> int:
    return len(self.momentos) - len(self.validas)


def analizar(momentos) -> Jornada:
  """Clasifica las marcaciones de UN empleado en UN día."""
  orden = sorted(momentos)
  validas: list[datetime] = []
  es_valida = []
  for m in orden:
    valida = not validas or m - validas[-1] >= REPETIDA_MIN
    if valida:
      validas.append(m)
    es_valida.append(valida)
  tipos, vistas = [], 0
  for valida in es_valida:
    if not valida:
      tipos.append(REPETIDA)
      continue
    tipos.append(ENTRADA if vistas % 2 == 0 else SALIDA)
    vistas += 1
  return Jornada(orden, tipos, validas)


def anulada(fila) -> bool:
  """True si la marcación se anuló a mano (las filas sin la columna `anulada` no lo están)."""
  try:
    return bool(fila["anulada"])
  except (KeyError, IndexError):
    return False


def tipos_de_marcaciones(filas) -> list[str]:
  """Tipo de cada fila (`fecha_hora`, `pin`), en el mismo orden que `filas` (cualquiera).

  Los pares se arman por empleado y por día. Las anuladas son ANULADA y no cuentan.
  """
  grupos: dict[tuple, list[tuple[datetime, int]]] = {}
  tipos = [ANULADA] * len(filas)
  for i, f in enumerate(filas):
    if anulada(f):
      continue
    momento = datetime.fromisoformat(f["fecha_hora"])
    grupos.setdefault((momento.date(), f["pin"]), []).append((momento, i))
  for miembros in grupos.values():
    miembros.sort()
    jornada = analizar(m for m, _ in miembros)
    for (_, i), tipo in zip(miembros, jornada.tipos):
      tipos[i] = tipo
  return tipos


# --- Formato -----------------------------------------------------------------------------

def fmt_hm(momento: datetime | None) -> str:
  return f"{momento:%H:%M}" if momento else ""


def fmt_horas(duracion: timedelta | None) -> str:
  """h:mm (minutos hacia abajo)."""
  if duracion is None:
    return ""
  minutos = max(0, int(duracion.total_seconds() // 60))
  return f"{minutos // 60}:{minutos % 60:02d}"


def fmt_fecha_hora(texto: str | None) -> str:
  """'2026-10-13 06:00:00' -> '13/10/2026 06:00' (vacío si no hay dato)."""
  if not texto:
    return ""
  try:
    return f"{datetime.fromisoformat(texto):%d/%m/%Y %H:%M}"
  except ValueError:
    return texto


def fecha_larga(dia: datetime) -> str:
  """'Martes 13 de octubre' (sin depender del idioma del sistema)."""
  return f"{DIAS[dia.weekday()].capitalize()} {dia.day} de {MESES[dia.month - 1]}"


# --- Vista Hoy ---------------------------------------------------------------------------

class Tramo(NamedTuple):
  """Posición del tramo en la franja, en % del ancho (0 = 07:00, 100 = 19:00)."""
  izq: float
  ancho: float
  abierto: bool       # sigue en el colegio: extremo abierto
  recorte_izq: bool   # empezó antes de las 07:00
  recorte_der: bool   # termina después de las 19:00
  falta: bool = False  # día pasado sin salida: solo se marca la entrada


class FilaHoy(NamedTuple):
  pin: str
  nombre: str | None        # None: PIN con marcaciones que no figura en Empleados
  estado: str
  entrada: datetime | None  # primera entrada del día
  salida: datetime | None   # última salida (solo si se retiró)
  horas: timedelta | None   # suma de los pares (si sigue en el colegio, el último hasta ahora)
  horas_parcial: bool       # True: son horas hasta ahora
  ultima: str               # fecha_hora de la última marcación válida ("" si no hay)
  celda_nueva: str          # "entrada" | "salida": la celda que se entinta al llegar `ultima`
  repetidas: int
  tramos: list[Tramo]       # uno por par entrada-salida (el último abierto si sigue)


class UltimaMarca(NamedTuple):
  """La marcación válida más reciente de hoy: el renglón vivo "Última marcación"."""
  pin: str
  nombre: str | None
  tipo: str    # Entrada | Salida
  hora: str    # HH:MM
  clave: str   # cambia cuando llega una marcación nueva (el cliente la compara para entintar)


class VistaHoy(NamedTuple):
  filas: list[FilaHoy]
  conteos: dict[str, int]   # todos, en_colegio, se_retiro, sin_marcar
  ahora_pct: float | None   # None: ahora fuera de la franja
  ahora: datetime
  ultima: UltimaMarca | None  # None: hoy no marcó nadie


def _pct(momento: datetime) -> float:
  minutos = momento.hour * 60 + momento.minute + momento.second / 60
  return (minutos - INICIO_MIN) / ESCALA_MIN * 100


def _acotar(pct: float) -> float:
  return min(100.0, max(0.0, pct))


def _tramo(inicio: datetime, fin: datetime, abierto: bool) -> Tramo:
  a, b = _pct(inicio), _pct(fin)
  izq = _acotar(a)
  ancho = max(0.0, _acotar(b) - izq)
  return Tramo(round(izq, 3), round(ancho, 3), abierto, a < 0, b > 100)


def _clave_nombre(texto: str) -> str:
  """Orden alfabético sin distinguir mayúsculas ni tildes."""
  base = unicodedata.normalize("NFD", texto.casefold())
  return "".join(c for c in base if not unicodedata.combining(c))


def vista_hoy(empleados, marcaciones, ahora: datetime, en_curso: bool = True) -> VistaHoy:
  """Arma la vista de un día (el de `ahora`).

  `empleados`: filas con pin y nombre. `marcaciones`: filas con pin y fecha_hora de ese día
  (los PIN que no están en `empleados` aparecen igual, sin nombre; las anuladas no cuentan).
  `en_curso`: False para un día pasado: quien no marcó la salida no suma horas "hasta ahora"
  (su tramo es solo la entrada, marcado como falta) y no hay línea "ahora".
  """
  por_pin: dict[str, list[datetime]] = {}
  for m in marcaciones:
    if anulada(m):
      continue
    momento = datetime.fromisoformat(m["fecha_hora"])
    if momento.date() == ahora.date():  # solo hoy, aunque lleguen marcaciones de otros días
      por_pin.setdefault(m["pin"], []).append(momento)
  nombres: dict[str, str | None] = {e["pin"]: e["nombre"] for e in empleados}
  for pin in por_pin:
    nombres.setdefault(pin, None)

  filas = []
  for pin, nombre in nombres.items():
    j = analizar(por_pin.get(pin, []))
    if not j.validas:
      estado = SIN_MARCAR
    elif j.abierta:
      estado = EN_COLEGIO
    else:
      estado = SE_RETIRO
    horas, parcial, tramos = None, False, []
    if j.validas:
      horas = j.horas
      for e, s in j.pares:
        if s:
          tramos.append(_tramo(e, s, False))
        elif en_curso:  # sigue en el colegio: el último tramo llega hasta ahora
          horas += max(timedelta(0), ahora - e)
          parcial = True
          tramos.append(_tramo(e, max(e, ahora), True))
        else:  # día pasado: se olvidó de marcar la salida
          tramos.append(_tramo(e, e, False)._replace(falta=True))
    ultima = j.validas[-1] if j.validas else None
    filas.append(FilaHoy(
      pin=pin, nombre=nombre, estado=estado, entrada=j.entrada, salida=j.salida, horas=horas,
      horas_parcial=parcial, ultima=f"{ultima:%Y-%m-%d %H:%M:%S}" if ultima else "",
      celda_nueva="salida" if estado == SE_RETIRO else ("entrada" if ultima else ""),
      repetidas=j.repetidas, tramos=tramos,
    ))

  def orden(f: FilaHoy):
    nombre = _clave_nombre(f.nombre or f"pin {f.pin}")
    if f.estado == SIN_MARCAR:
      return (1, datetime.min, nombre, f.pin)
    return (0, f.entrada, nombre, f.pin)

  filas.sort(key=orden)
  conteos = {"todos": len(filas)}
  for estado in ESTADOS:
    conteos[estado] = sum(1 for f in filas if f.estado == estado)
  ahora_pct = _pct(ahora) if en_curso else -1.0
  con_marca = [f for f in filas if f.ultima]
  ultima = None
  if con_marca:
    f = max(con_marca, key=lambda f: (f.ultima, f.pin))
    ultima = UltimaMarca(f.pin, f.nombre, SALIDA if f.estado == SE_RETIRO else ENTRADA,
                         f.ultima[11:16], f"{f.pin}|{f.ultima}")
  return VistaHoy(filas, conteos, round(ahora_pct, 3) if 0 <= ahora_pct <= 100 else None, ahora,
                  ultima)
