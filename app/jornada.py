"""La jornada del día: una sola regla para la vista Hoy, la columna Tipo y el Excel.

Reglas (las mismas que documenta app/reports.py):
- Primera marcación válida del día = entrada; última = salida. Las del medio son intermedias.
- Una marcación a menos de 2 minutos de la última válida es repetida y se ignora.
- Una sola válida: sigue en el colegio (sin salida). Ninguna: sin marcar.
- No se cruza la medianoche: cada día calendario se analiza por separado.

Todo son funciones puras (el "ahora" se inyecta), así se testean sin base ni reloj.
"""
import unicodedata
from datetime import datetime, timedelta
from typing import NamedTuple

REPETIDA_MIN = timedelta(minutes=2)

ENTRADA, SALIDA, INTERMEDIA, REPETIDA = "Entrada", "Salida", "Intermedia", "Repetida"

EN_COLEGIO, SE_RETIRO, SIN_MARCAR = "en_colegio", "se_retiro", "sin_marcar"
ESTADOS = {EN_COLEGIO: "En el colegio", SE_RETIRO: "Se retiró", SIN_MARCAR: "Sin marcar"}

# Franja de "La jornada": de 07:00 a 19:00 (horario diurno)
INICIO_MIN = 7 * 60
FIN_MIN = 19 * 60
ESCALA_MIN = FIN_MIN - INICIO_MIN
MARCAS_HORA = list(range(7, 20, 2))  # 07 09 11 13 15 17 19 en el encabezado

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


class Jornada(NamedTuple):
  momentos: list[datetime]  # todas las marcaciones, en orden
  tipos: list[str]          # tipo de cada una (mismo orden que `momentos`)
  validas: list[datetime]   # las que cuentan (sin repetidas)

  @property
  def entrada(self) -> datetime | None:
    return self.validas[0] if self.validas else None

  @property
  def salida(self) -> datetime | None:
    return self.validas[-1] if len(self.validas) > 1 else None

  @property
  def intermedias(self) -> list[datetime]:
    return self.validas[1:-1]

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
    vistas += 1
    if vistas == 1:
      tipos.append(ENTRADA)
    elif vistas == len(validas):
      tipos.append(SALIDA)
    else:
      tipos.append(INTERMEDIA)
  return Jornada(orden, tipos, validas)


def tipos_de_marcaciones(filas) -> list[str]:
  """Tipo de cada fila (`fecha_hora`, `pin`), en el mismo orden que `filas` (cualquiera)."""
  grupos: dict[tuple, list[tuple[datetime, int]]] = {}
  for i, f in enumerate(filas):
    momento = datetime.fromisoformat(f["fecha_hora"])
    grupos.setdefault((momento.date(), f["pin"]), []).append((momento, i))
  tipos = [""] * len(filas)
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


class FilaHoy(NamedTuple):
  pin: str
  nombre: str | None        # None: PIN con marcaciones que no figura en Empleados
  estado: str
  entrada: datetime | None
  salida: datetime | None
  horas: timedelta | None   # salida - entrada, o (si sigue) ahora - entrada
  horas_parcial: bool       # True: son horas hasta ahora
  ultima: str               # fecha_hora de la última marcación válida ("" si no hay)
  celda_nueva: str          # "entrada" | "salida": la celda donde cae `ultima`
  repetidas: int
  tramo: Tramo | None
  ticks: list[float]        # intermedias dentro de la franja, en %


class VistaHoy(NamedTuple):
  filas: list[FilaHoy]
  conteos: dict[str, int]   # todos, en_colegio, se_retiro, sin_marcar
  ahora_pct: float | None   # None: ahora fuera de la franja
  ahora: datetime


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


def vista_hoy(empleados, marcaciones, ahora: datetime) -> VistaHoy:
  """Arma la vista de hoy.

  `empleados`: filas con pin y nombre. `marcaciones`: filas con pin y fecha_hora de HOY
  (los PIN que no están en `empleados` aparecen igual, sin nombre).
  """
  por_pin: dict[str, list[datetime]] = {}
  for m in marcaciones:
    momento = datetime.fromisoformat(m["fecha_hora"])
    if momento.date() == ahora.date():  # solo hoy, aunque lleguen marcaciones de otros días
      por_pin.setdefault(m["pin"], []).append(momento)
  nombres: dict[str, str | None] = {e["pin"]: e["nombre"] for e in empleados}
  for pin in por_pin:
    nombres.setdefault(pin, None)

  filas = []
  for pin, nombre in nombres.items():
    j = analizar(por_pin.get(pin, []))
    entrada, salida = j.entrada, j.salida
    if entrada is None:
      estado = SIN_MARCAR
    elif salida is None:
      estado = EN_COLEGIO
    else:
      estado = SE_RETIRO
    horas, parcial, tramo = None, False, None
    if estado == SE_RETIRO:
      horas, tramo = salida - entrada, _tramo(entrada, salida, False)
    elif estado == EN_COLEGIO:
      horas, parcial = max(timedelta(0), ahora - entrada), True
      tramo = _tramo(entrada, max(entrada, ahora), True)
    ultima = j.validas[-1] if j.validas else None
    filas.append(FilaHoy(
      pin=pin, nombre=nombre, estado=estado, entrada=entrada, salida=salida, horas=horas,
      horas_parcial=parcial, ultima=f"{ultima:%Y-%m-%d %H:%M:%S}" if ultima else "",
      celda_nueva="salida" if estado == SE_RETIRO else ("entrada" if ultima else ""),
      repetidas=j.repetidas, tramo=tramo,
      ticks=[round(_pct(t), 3) for t in j.intermedias if 0 <= _pct(t) <= 100],
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
  ahora_pct = _pct(ahora)
  return VistaHoy(filas, conteos, round(ahora_pct, 3) if 0 <= ahora_pct <= 100 else None, ahora)
