"""Reporte de asistencia a Excel (openpyxl).

`resumen_por_dia` es una función pura (se testea sin Excel); `generar_excel` solo escribe.

Reglas del resumen por día (una fila por empleado y día calendario):
- Entrada = primera marcación del día; Salida = última. Horas = Salida - Entrada.
  No contempla almuerzo, turnos ni horarios.
- Repetidas: una marcación a menos de 2 minutos de la última marcación válida (típico de
  marcar dos veces seguidas) se ignora. Se cuentan en la Observación; Cantidad es el total real.
- Una sola marcación válida: sin Salida, 0 horas. Más de dos: se usan la primera y la última.
- No se cruza la medianoche: cada día calendario se calcula por separado (un turno nocturno
  aparece como dos días incompletos).
"""
from datetime import datetime, timedelta
from io import BytesIO
from typing import NamedTuple

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# Tope de seguridad de filas del Excel (si hay más se exportan las más nuevas y se avisa en "Info")
LIMITE_EXCEL = 200_000
REPETIDA = timedelta(minutes=2)
VERIFICACION_CARA = 15  # deducido, no verificado
FORMATO_FECHA, FORMATO_HORA, FORMATO_HORAS = "dd/mm/yyyy", "hh:mm:ss", "[h]:mm"
NOTAS = [
  "Horas = última - primera marcación del día; no contempla almuerzo, turnos ni horarios.",
  "Marcaciones a menos de 2 minutos de la anterior se ignoran (se cuentan en Observación).",
  "Cada día calendario se calcula por separado: no se cruza la medianoche.",
]


class Resumen(NamedTuple):
  fecha: datetime  # solo la parte de fecha
  pin: str
  nombre: str
  entrada: datetime
  salida: datetime | None
  cantidad: int  # marcaciones reales del día (con repetidas)
  horas: timedelta
  observacion: str


def _clave_pin(pin: str) -> tuple:
  return (0, int(pin), pin) if pin.isdigit() else (1, 0, pin)


def resumen_por_dia(filas) -> list[Resumen]:
  """`filas`: marcaciones con `fecha_hora` (YYYY-MM-DD HH:MM:SS), `pin` y `nombre` (o None).

  Devuelve una fila por (día, empleado), ordenadas por día y luego PIN.
  """
  grupos: dict[tuple, tuple[str, list[datetime]]] = {}
  for f in filas:
    momento = datetime.fromisoformat(f["fecha_hora"])
    _, momentos = grupos.setdefault((momento.date(), f["pin"]), (f["nombre"] or "", []))
    momentos.append(momento)
  resultado = []
  for (dia, pin), (nombre, momentos) in sorted(
      grupos.items(), key=lambda kv: (kv[0][0], _clave_pin(kv[0][1]))):
    validas = []
    for m in sorted(momentos):
      if not validas or m - validas[-1] >= REPETIDA:
        validas.append(m)
    obs = []
    if (repetidas := len(momentos) - len(validas)):
      obs.append(f"{repetidas} repetida(s) ignorada(s)")
    if len(validas) == 1:
      obs.append("Falta la salida (o la entrada)")
    elif len(validas) > 2:
      obs.append(f"{len(validas) - 2} marcaciones intermedias (se usó la primera y la última)")
    salida = validas[-1] if len(validas) > 1 else None
    resultado.append(Resumen(
      fecha=datetime.combine(dia, datetime.min.time()), pin=pin, nombre=nombre,
      entrada=validas[0], salida=salida, cantidad=len(momentos),
      horas=salida - validas[0] if salida else timedelta(0), observacion="; ".join(obs),
    ))
  return resultado


def _celda_pin(pin: str):
  """Número si es un entero sin ceros a la izquierda; si no, el texto tal cual."""
  return int(pin) if pin.isdigit() and str(int(pin)) == pin else pin


def _encabezados(ws, titulos: list[str], anchos: list[int]) -> None:
  ws.append(titulos)
  for celda in ws[1]:
    celda.font = Font(bold=True)
    celda.fill = PatternFill("solid", fgColor="E7E9ED")
  for i, ancho in enumerate(anchos, start=1):
    ws.column_dimensions[get_column_letter(i)].width = ancho
  ws.freeze_panes = "A2"


def _dias(horas: timedelta) -> float:
  return horas.total_seconds() / 86400  # duración de Excel: fracción de día


def generar_excel(filas, desde: str | None, hasta: str | None, pin: str | None,
                  nombre_pin: str | None = None, truncado: bool = False,
                  generado: datetime | None = None) -> bytes:
  """Arma el .xlsx (hojas Detalle, Resumen por día e Info) y lo devuelve como bytes.

  `filas`: marcaciones en orden ascendente con fecha_hora, pin, nombre, verificacion y sn.
  """
  filas = list(filas)
  wb = Workbook()

  ws = wb.active
  ws.title = "Detalle"
  _encabezados(ws, ["Fecha", "Hora", "PIN", "Nombre", "Verificación", "SN"],
               [12, 10, 10, 26, 14, 18])
  for f in filas:
    momento = datetime.fromisoformat(f["fecha_hora"])
    v = f["verificacion"]
    ws.append([momento.date(), momento.time(), _celda_pin(f["pin"]), f["nombre"] or "",
               "Cara" if v == VERIFICACION_CARA else ("" if v is None else v), f["sn"]])
    ws.cell(ws.max_row, 1).number_format = FORMATO_FECHA
    ws.cell(ws.max_row, 2).number_format = FORMATO_HORA
    ws.cell(ws.max_row, 5).alignment = Alignment(horizontal="left")
  ws.auto_filter.ref = f"A1:F{ws.max_row}"

  ws = wb.create_sheet("Resumen por día")
  _encabezados(ws, ["Fecha", "PIN", "Nombre", "Entrada", "Salida", "Cantidad",
                    "Horas trabajadas", "Observación"], [12, 10, 26, 10, 10, 10, 17, 60])
  total = timedelta(0)
  for r in resumen_por_dia(filas):
    total += r.horas
    ws.append([r.fecha.date(), _celda_pin(r.pin), r.nombre, r.entrada.time(),
               r.salida.time() if r.salida else None, r.cantidad, _dias(r.horas), r.observacion])
    fila = ws.max_row
    ws.cell(fila, 1).number_format = FORMATO_FECHA
    ws.cell(fila, 4).number_format = ws.cell(fila, 5).number_format = FORMATO_HORA
    ws.cell(fila, 7).number_format = FORMATO_HORAS
  ws.auto_filter.ref = f"A1:H{ws.max_row}"  # sin la fila Total
  ws.append(["Total", None, None, None, None, None, _dias(total)])
  ws.cell(ws.max_row, 7).number_format = FORMATO_HORAS
  for celda in ws[ws.max_row]:
    celda.font = Font(bold=True)
  ws.append([])
  for nota in NOTAS:
    ws.append([nota])
    ws.cell(ws.max_row, 1).font = Font(italic=True, color="666666")

  ws = wb.create_sheet("Info")
  ws.column_dimensions["A"].width = 24
  ws.column_dimensions["B"].width = 70
  generado = generado or datetime.now()
  info = [
    ("Desde", _fecha_txt(desde, "sin límite")),
    ("Hasta", _fecha_txt(hasta, "sin límite")),
    ("Empleado", "Todos" if not pin else (f"{pin} - {nombre_pin}" if nombre_pin else pin)),
    ("Marcaciones exportadas", len(filas)),
    ("Generado", generado.strftime("%d/%m/%Y %H:%M:%S")),
  ]
  if truncado:
    info.append(("Aviso", f"Había más de {LIMITE_EXCEL} marcaciones: se exportaron solo las más "
                          "nuevas. Acotá el rango de fechas o elegí un empleado."))
  info += [("Nota", n) for n in NOTAS]
  for etiqueta, valor in info:
    ws.append([etiqueta, valor])
    ws.cell(ws.max_row, 1).font = Font(bold=True)
    ws.cell(ws.max_row, 2).alignment = Alignment(horizontal="left")

  salida = BytesIO()
  wb.save(salida)
  return salida.getvalue()


def _fecha_txt(iso: str | None, vacio: str) -> str:
  return datetime.fromisoformat(iso).strftime("%d/%m/%Y") if iso else vacio
