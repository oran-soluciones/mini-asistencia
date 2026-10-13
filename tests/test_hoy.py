import re
from datetime import datetime

import pytest

from app import db
from app.iclock import parse_users
from test_panel import SN, cargar, marcacion

AHORA = datetime(2026, 10, 13, 12, 0, 0)  # un martes
HOY = "2026-10-13"


@pytest.fixture(autouse=True)
def hora(monkeypatch):
  monkeypatch.setattr(db, "ahora", lambda: AHORA)


def emp(db_path, usuarios):
  db.upsert_empleados(SN, parse_users(usuarios), db_path)


def nombres_en_orden(html):
  return re.findall(r'<span class="nombre">([^<]+)</span>', html)


def con_gente(db_path):
  emp(db_path, "USER PIN=1\tName=Zoe Paz\tPri=0\nUSER PIN=2\tName=Ana Gil\tPri=0\n"
               "USER PIN=3\tName=Beto Sosa\tPri=0\nUSER PIN=4\tName=Carla Roca\tPri=0\n")
  cargar(db_path, [
    marcacion(1, f"{HOY} 08:00:00"), marcacion(1, f"{HOY} 11:00:00"),   # Zoe se retiró
    marcacion(3, f"{HOY} 07:30:00"), marcacion(3, f"{HOY} 07:31:00"),   # Beto, con una repetida
    marcacion(77, f"{HOY} 09:15:00"),                                     # PIN sin empleado
    marcacion(4, "2026-10-12 08:00:00"),                                  # Carla: solo ayer
  ])


def test_hoy_muestra_fecha_hora_y_conteos(client, db_path):
  con_gente(db_path)
  html = client.get("/hoy").text
  assert "<h1>Martes 13 de octubre</h1>" in html
  assert re.search(r"<time datetime=\"2026-10-13T12:00\">12:00</time>", html)
  conteos = re.findall(r'data-estado="([a-z_]*)">(?:<span class="punto"[^>]*></span>)?[^<]*<span class="n">(\d+)', html)
  assert conteos == [("", "5"), ("en_colegio", "2"), ("se_retiro", "1"), ("sin_marcar", "2")]
  assert "Todos" in html and "En el colegio" in html and "Se retiraron" in html


def test_hoy_estados_orden_y_pin_sin_nombre(client, db_path):
  con_gente(db_path)
  html = client.get("/hoy").text
  # Por entrada: Beto 07:30, Zoe 08:00, PIN 77 09:15; sin marcar al final por nombre
  assert nombres_en_orden(html) == [
    "Beto Sosa", "Zoe Paz", "PIN 77 · sin nombre", "Ana Gil", "Carla Roca"]
  fila_zoe = re.search(r'<tr class="fila"[^>]*data-pin="1".*?</tr>', html, re.S).group(0)
  assert "Se retiró" in fila_zoe and ">08:00<" in fila_zoe and ">11:00<" in fila_zoe
  assert 'class="horas">3:00<' in fila_zoe
  fila_beto = re.search(r'<tr class="fila"[^>]*data-pin="3".*?</tr>', html, re.S).group(0)
  assert "En el colegio" in fila_beto and ">07:30<" in fila_beto  # la repetida de 07:31 no cuenta
  assert 'class="horas parcial">4:30<' in fila_beto and "hasta ahora" in fila_beto
  assert 'data-ultima="2026-10-13 07:30:00"' in fila_beto and 'data-celda="entrada"' in fila_beto
  fila_ana = re.search(r'<tr class="fila"[^>]*data-pin="2".*?</tr>', html, re.S).group(0)
  assert "Sin marcar" in fila_ana and 'data-ultima=""' in fila_ana
  assert "No figura en Empleados" in html


def test_hoy_la_jornada_posiciones_y_linea_ahora(client, db_path):
  con_gente(db_path)
  html = client.get("/hoy").text
  assert 'style="--ahora: 41.667%"' in html  # 12:00 sobre 07:00-19:00
  zoe = re.search(r'<tr class="fila"[^>]*data-pin="1".*?</tr>', html, re.S).group(0)
  assert 'class="tramo"' in zoe and "left: 8.333%; width: 25.0%" in zoe  # 08:00 -> 11:00
  beto = re.search(r'<tr class="fila"[^>]*data-pin="3".*?</tr>', html, re.S).group(0)
  assert 'class="tramo abierto"' in beto and "left: 4.167%; width: 37.5%" in beto  # 07:30 -> ahora
  ana = re.search(r'<tr class="fila"[^>]*data-pin="2".*?</tr>', html, re.S).group(0)
  assert "tramo" not in ana
  assert html.count('class="marca-hora"') == 7 and ">07<" in html and ">19<" in html


def test_hoy_fuera_de_horario_no_dibuja_la_linea_ahora(client, db_path, monkeypatch):
  monkeypatch.setattr(db, "ahora", lambda: datetime(2026, 10, 13, 21, 0))
  emp(db_path, "USER PIN=1\tName=Zoe Paz\tPri=0\n")
  html = client.get("/hoy").text
  assert "sin-ahora" in html and "--ahora" not in html and "escala-ahora" not in html


def test_hoy_nadie_marco(client, db_path):
  emp(db_path, "USER PIN=1\tName=Zoe Paz\tPri=0\n")
  html = client.get("/hoy").text
  assert "Todavía nadie marcó hoy. Las marcaciones aparecen solas apenas llegan del reloj." in html
  assert "Sin marcar" in html
  cargar(db_path, [marcacion(1, f"{HOY} 08:00:00")])
  assert "Todavía nadie marcó hoy" not in client.get("/hoy").text


def test_hoy_sin_personal_estado_vacio(client, db_path):
  html = client.get("/hoy").text
  assert "Todavía no hay personal para mostrar." in html and 'href="/empleados"' in html
  assert "<table" not in html


def test_hoy_parcial_se_refresca_cada_5_segundos(client, db_path):
  con_gente(db_path)
  html = client.get("/hoy").text
  assert 'hx-get="/hoy/tabla"' in html and 'hx-trigger="every 5s"' in html
  assert "hx-swap-oob" not in html  # en la página completa no hace falta
  parcial = client.get("/hoy/tabla").text
  assert "<html" not in parcial and 'id="hoy-planilla"' in parcial
  assert 'id="hoy-titulo"' in parcial and 'id="hoy-conteos"' in parcial
  assert parcial.count('hx-swap-oob="true"') == 2  # título y resumen
  # El buscador no está en el parcial: se conserva lo que la persona escribió
  assert 'id="buscar"' not in parcial and 'id="buscar"' in html
  assert nombres_en_orden(parcial) == nombres_en_orden(html)


def test_hoy_el_parcial_trae_la_marcacion_nueva(client, db_path):
  con_gente(db_path)
  antes = client.get("/hoy/tabla").text
  assert 'data-pin="2" data-estado="sin_marcar" data-ultima=""' in antes
  cargar(db_path, [marcacion(2, f"{HOY} 11:45:10")])
  despues = client.get("/hoy/tabla").text
  assert 'data-pin="2" data-estado="en_colegio" data-ultima="2026-10-13 11:45:10"' in despues


def test_hoy_el_filtro_de_la_url_se_repone_en_la_pagina(client, db_path):
  con_gente(db_path)
  html = client.get("/hoy?estado=se_retiro&q=zoe").text
  assert 'data-filtro="se_retiro"' in html and 'value="zoe"' in html
  # Valores raros: estado inválido se ignora y el texto va escapado
  html = client.get('/hoy?estado=hack&q="><script>alert(1)</script>').text
  assert 'data-filtro=""' in html and "<script>alert(1)</script>" not in html


def test_hoy_escapa_nombres(client, db_path):
  emp(db_path, "USER PIN=5\tName=<img src=x onerror=1>\tPri=0\n")
  html = client.get("/hoy").text
  assert "<img src=x" not in html and "&lt;img src=x onerror=1&gt;" in html


def test_hoy_navegacion_y_accesibilidad(client, db_path):
  html = client.get("/hoy").text
  assert re.search(r'<a href="/hoy" aria-current="page">', html)
  for ruta in ("/marcaciones", "/empleados", "/configuracion"):
    assert f'<a href="{ruta}">' in html
  assert 'class="saltar"' in html and '<main id="contenido">' in html
  assert 'src="/static/panel.js"' in html
