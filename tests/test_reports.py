from datetime import date, datetime, time, timedelta
from io import BytesIO

from openpyxl import load_workbook

from app import db, panel, reports
from app.iclock import parse_users
from conftest import fixture_text
from test_panel import SN, cargar, con_datos, marcacion


def fila(pin, fecha_hora, nombre="Ana", verificacion=15):
  return {"pin": pin, "fecha_hora": fecha_hora, "nombre": nombre,
          "verificacion": verificacion, "sn": SN}


def horas(r):
  return r.horas.total_seconds() / 3600


def test_resumen_par_simple():
  [r] = reports.resumen_por_dia([fila("7", "2026-10-12 08:00:00"), fila("7", "2026-10-12 17:00:00")])
  assert (r.pin, r.nombre, r.cantidad) == ("7", "Ana", 2)
  assert r.fecha.date() == date(2026, 10, 12)
  assert r.entrada == datetime(2026, 10, 12, 8) and r.salida == datetime(2026, 10, 12, 17)
  assert horas(r) == 9 and r.observacion == ""


def test_resumen_una_sola_marcacion():
  [r] = reports.resumen_por_dia([fila("7", "2026-10-12 08:00:00")])
  assert r.entrada == datetime(2026, 10, 12, 8) and r.salida is None
  assert r.horas == timedelta(0) and r.cantidad == 1
  assert r.observacion == "Falta la salida (o la entrada)"


def test_resumen_repetidas_a_menos_de_2_minutos():
  [r] = reports.resumen_por_dia([
    fila("7", "2026-10-12 08:00:00"), fila("7", "2026-10-12 08:01:59"),
    fila("7", "2026-10-12 17:00:00"), fila("7", "2026-10-12 17:00:30"),
  ])
  assert r.cantidad == 4 and horas(r) == 9
  assert r.entrada == datetime(2026, 10, 12, 8) and r.salida == datetime(2026, 10, 12, 17)
  assert r.observacion == "2 repetida(s) ignorada(s)"
  # justo 2 minutos ya no es repetida
  [r] = reports.resumen_por_dia([fila("7", "2026-10-12 08:00:00"), fila("7", "2026-10-12 08:02:00")])
  assert r.observacion == "" and r.horas == timedelta(minutes=2)


def test_resumen_solo_repetidas_queda_sin_salida():
  [r] = reports.resumen_por_dia([fila("7", "2026-10-12 08:00:00"), fila("7", "2026-10-12 08:00:40")])
  assert r.salida is None and r.horas == timedelta(0) and r.cantidad == 2
  assert r.observacion == "1 repetida(s) ignorada(s); Falta la salida (o la entrada)"


def test_resumen_mas_de_dos_usa_primera_y_ultima():
  [r] = reports.resumen_por_dia([
    fila("7", "2026-10-12 17:00:00"), fila("7", "2026-10-12 08:00:00"),  # desordenadas
    fila("7", "2026-10-12 12:00:00"), fila("7", "2026-10-12 13:00:00"),
  ])
  assert r.cantidad == 4 and horas(r) == 9
  assert r.observacion == "2 marcaciones intermedias (se usó la primera y la última)"


def test_resumen_dos_empleados_y_dos_dias_ordenados_por_dia_y_pin():
  res = reports.resumen_por_dia([
    fila("10", "2026-10-11 08:00:00", "Zoe"), fila("10", "2026-10-11 16:00:00", "Zoe"),
    fila("9", "2026-10-12 09:00:00", "Ana"), fila("9", "2026-10-12 12:30:00", "Ana"),
    fila("9", "2026-10-11 08:00:00", "Ana"), fila("9", "2026-10-11 17:00:00", "Ana"),
    fila("10", "2026-10-12 10:00:00", "Zoe"),
  ])
  assert [(r.fecha.date().day, r.pin) for r in res] == [(11, "9"), (11, "10"), (12, "9"), (12, "10")]
  assert [horas(r) for r in res] == [9, 8, 3.5, 0]


def test_resumen_pin_sin_nombre():
  [r] = reports.resumen_por_dia([fila("99", "2026-10-12 08:00:00", None)])
  assert r.nombre == ""


def test_resumen_no_cruza_la_medianoche():
  res = reports.resumen_por_dia([fila("7", "2026-10-11 22:00:00"), fila("7", "2026-10-12 06:00:00")])
  assert len(res) == 2 and all(r.salida is None for r in res)


# --- Endpoint -----------------------------------------------------------------------

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def abrir(r):
  return load_workbook(BytesIO(r.content))


def datos(ws):
  return [[c.value for c in row] for row in ws.iter_rows(min_row=2)]


def test_excel_respuesta_y_hojas(client, db_path):
  con_datos(db_path)
  r = client.get("/marcaciones/excel?desde=&hasta=")
  assert r.status_code == 200
  assert r.headers["content-type"] == XLSX
  assert r.headers["content-disposition"] == 'attachment; filename="asistencia_todo_todo.xlsx"'
  wb = abrir(r)
  assert wb.sheetnames == ["Detalle", "Resumen por día", "Info"]
  ws = wb["Detalle"]
  assert [c.value for c in ws[1]] == ["Fecha", "Hora", "PIN", "Nombre", "Verificación", "SN"]
  assert ws.freeze_panes == "A2" and ws.auto_filter.ref == "A1:F6"
  assert ws["A1"].font.b
  filas = datos(ws)
  assert len(filas) == 5
  # Orden ascendente; Fecha y Hora son valores reales con formato
  assert filas[0][0] == datetime(2026, 10, 10) and filas[0][1] == time(8, 0, 0)
  assert filas[-1][2:] == [99, None, "Cara", SN]  # PIN sin empleado: nombre vacío
  assert ws["A2"].number_format == "dd/mm/yyyy" and ws["B2"].number_format == "hh:mm:ss"
  assert [f[0] for f in filas] == sorted(f[0] for f in filas)
  assert filas[0][3] == "Ana Gómez" and filas[0][4] == "Cara"
  assert [f[4] for f in filas].count(1) == 1  # verificación distinta de 15: el número


def test_excel_resumen_horas_y_total(client, db_path):
  db.upsert_empleados(SN, parse_users(fixture_text("operlog_usuarios.txt")), db_path)
  cargar(db_path, [
    marcacion(7, "2026-10-12 08:00:00"), marcacion(7, "2026-10-12 17:00:00"),
    marcacion(8, "2026-10-12 09:00:00"), marcacion(8, "2026-10-12 09:01:00"),
    marcacion(8, "2026-10-12 12:00:00"), marcacion(8, "2026-10-12 13:30:00"),
    marcacion(99, "2026-10-13 10:00:00"),
  ])
  ws = abrir(client.get("/marcaciones/excel?desde=&hasta=&pin="))["Resumen por día"]
  assert [c.value for c in ws[1]] == [
    "Fecha", "PIN", "Nombre", "Entrada", "Salida", "Cantidad", "Horas trabajadas", "Observación"]
  assert ws.freeze_panes == "A2" and ws.auto_filter.ref == "A1:H4"
  [a, b, c] = datos(ws)[:3]
  assert a[:6] == [datetime(2026, 10, 12), 7, "Ana Gómez", time(8), time(17), 2]
  assert a[6] == timedelta(hours=9) and a[7] is None
  assert b[1:6] == [8, "Luis Pérez", time(9), time(13, 30), 4]
  assert b[6] == timedelta(hours=4.5) and "1 repetida(s)" in b[7] and "1 marcaciones intermedias" in b[7]
  assert c[1:6] == [99, None, time(10), None, 1]
  assert c[6] == timedelta(0) and "Falta la salida" in c[7]
  assert ws["G2"].number_format == "[h]:mm"
  total = [row for row in ws.iter_rows() if row[0].value == "Total"][0]
  assert total[6].value == timedelta(hours=13.5) and total[6].number_format == "[h]:mm"
  notas = " ".join(str(row[0].value) for row in ws.iter_rows() if row[0].value)
  assert "no contempla almuerzo, turnos ni horarios" in notas


def test_excel_info(client, db_path):
  con_datos(db_path)
  ws = abrir(client.get("/marcaciones/excel?desde=2026-10-11&hasta=2026-10-12&pin=8"))["Info"]
  info = {row[0].value: row[1].value for row in ws.iter_rows()}
  assert info["Desde"] == "11/10/2026" and info["Hasta"] == "12/10/2026"
  assert info["Empleado"] == "8 - Luis Pérez" and info["Marcaciones exportadas"] == 2
  assert info["Generado"]


def test_excel_respeta_filtros(client, db_path):
  con_datos(db_path)
  r = client.get("/marcaciones/excel?desde=2026-10-11&hasta=2026-10-11")
  assert r.headers["content-disposition"] == \
    'attachment; filename="asistencia_2026-10-11_2026-10-11.xlsx"'
  assert len(datos(abrir(r)["Detalle"])) == 2
  assert len(datos(abrir(client.get("/marcaciones/excel?desde=2026-10-12&hasta="))["Detalle"])) == 2
  r = client.get("/marcaciones/excel?desde=&hasta=2026-10-10")
  assert len(datos(abrir(r)["Detalle"])) == 1
  assert 'filename="asistencia_todo_2026-10-10.xlsx"' in r.headers["content-disposition"]
  filas = datos(abrir(client.get("/marcaciones/excel?desde=&hasta=&pin=8"))["Detalle"])
  assert [f[2] for f in filas] == [8, 8]


def test_excel_sin_filtros_es_hoy(client, db_path):
  hoy = date.today().isoformat()
  cargar(db_path, [marcacion(7, f"{hoy} 07:30:00"), marcacion(7, "2026-01-01 07:30:00")])
  r = client.get("/marcaciones/excel")
  assert f"asistencia_{hoy}_{hoy}.xlsx" in r.headers["content-disposition"]
  assert len(datos(abrir(r)["Detalle"])) == 1


def test_excel_sin_limite_de_la_tabla_y_con_tope(client, db_path, monkeypatch):
  monkeypatch.setattr(panel, "LIMITE_FILAS", 2)
  con_datos(db_path)
  wb = abrir(client.get("/marcaciones/excel?desde=&hasta="))
  assert len(datos(wb["Detalle"])) == 5
  monkeypatch.setattr(reports, "LIMITE_EXCEL", 3)
  wb = abrir(client.get("/marcaciones/excel?desde=&hasta="))
  filas = datos(wb["Detalle"])
  assert len(filas) == 3 and filas[0][0] == datetime(2026, 10, 11)  # las 3 más nuevas
  assert any(row[0].value == "Aviso" for row in wb["Info"].iter_rows())


def test_excel_vacio(client, db_path):
  wb = abrir(client.get("/marcaciones/excel?desde=&hasta="))
  assert datos(wb["Detalle"]) == []
  assert wb["Resumen por día"]["A2"].value == "Total"


def test_boton_exportar_en_la_pagina(client, db_path):
  html = client.get("/marcaciones").text
  assert 'formaction="/marcaciones/excel"' in html and "Exportar a Excel" in html


def test_excel_rechaza_clientes_no_locales(client_externo, db_path):
  assert client_externo.get("/marcaciones/excel").status_code == 403
  assert not db_path.exists()


# --- Favicon ------------------------------------------------------------------------

def test_favicon_no_crea_sample(client, tmp_path):
  r = client.get("/favicon.ico")
  assert r.status_code == 204
  assert not list(tmp_path.glob("*.txt"))
  assert 'href="/static/icono.svg"' in client.get("/marcaciones").text
  assert client.get("/static/icono.svg").status_code == 200
