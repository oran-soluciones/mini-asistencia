from datetime import date

from app import db, panel
from app.iclock import parse_attlog, parse_users
from conftest import fixture_text

SN = "TESTSN0001"


def marcacion(pin, fecha_hora, verificacion=15):
  return f"{pin}\t{fecha_hora}\t0\t{verificacion}\t0\t0\t0\t0\t0\t0\t"


def cargar(db_path, lineas):
  db.insert_marcaciones(SN, parse_attlog("\n".join(lineas) + "\n"), db_path)


def con_datos(db_path):
  db.upsert_empleados(SN, parse_users(fixture_text("operlog_usuarios.txt")), db_path)
  cargar(db_path, [
    marcacion(7, "2026-10-10 08:00:00"),
    marcacion(7, "2026-10-11 08:01:00"),
    marcacion(8, "2026-10-11 09:00:00", verificacion=1),
    marcacion(8, "2026-10-12 10:00:00"),
    marcacion(99, "2026-10-12 11:00:00"),  # PIN sin empleado cargado
  ])


def filas_en(html):
  return html.count("<tr>") - 1  # menos el encabezado


def test_raiz_redirige_a_marcaciones(client):
  r = client.get("/", follow_redirects=False)
  assert r.status_code in (302, 307)
  assert r.headers["location"] == "/marcaciones"


def test_marcaciones_muestra_filas_nombre_y_verificacion(client, db_path):
  con_datos(db_path)
  html = client.get("/marcaciones?desde=&hasta=").text
  assert "mini-asistencia" in html
  assert "2026-10-11 08:01:00" in html and "Ana Gómez" in html
  assert filas_en(html) == 5
  assert "Cara" in html and "no verificado" in html  # verificación 15
  assert "<td>1</td>" in html  # verificación 1 se muestra como número
  # Más nueva primero
  assert html.index("2026-10-12 11:00:00") < html.index("2026-10-10 08:00:00")
  # El PIN sin empleado se muestra igual, con el nombre vacío
  assert "<td>99</td>\n        <td></td>" in html


def test_marcaciones_por_defecto_muestra_hoy(client, db_path):
  hoy = date.today().isoformat()
  cargar(db_path, [marcacion(7, f"{hoy} 07:30:00"), marcacion(7, "2026-01-01 07:30:00")])
  html = client.get("/marcaciones").text
  assert f"{hoy} 07:30:00" in html and "2026-01-01 07:30:00" not in html
  assert f'value="{hoy}"' in html


def test_filtro_desde_hasta_inclusivo(client, db_path):
  con_datos(db_path)
  html = client.get("/marcaciones?desde=2026-10-11&hasta=2026-10-11").text
  assert filas_en(html) == 2
  assert "2026-10-11 08:01:00" in html and "2026-10-11 09:00:00" in html
  assert filas_en(client.get("/marcaciones?desde=2026-10-12&hasta=").text) == 2
  assert filas_en(client.get("/marcaciones?desde=&hasta=2026-10-10").text) == 1


def test_filtro_por_pin(client, db_path):
  con_datos(db_path)
  html = client.get("/marcaciones?desde=&hasta=&pin=8").text
  assert filas_en(html) == 2 and "Luis Pérez" in html
  assert "<td>Ana Gómez</td>" not in html
  html = client.get("/marcaciones?desde=2026-10-11&hasta=2026-10-11&pin=8").text
  assert filas_en(html) == 1


def test_select_de_pins_incluye_empleados_y_pins_de_marcaciones(client, db_path):
  con_datos(db_path)
  html = client.get("/marcaciones?desde=&hasta=&pin=8").text
  assert '<option value="7">7 - Ana Gómez</option>' in html
  assert '<option value="8" selected>8 - Luis Pérez</option>' in html
  assert '<option value="99">99</option>' in html


def test_fecha_invalida_se_ignora(client, db_path):
  con_datos(db_path)
  assert filas_en(client.get("/marcaciones?desde=basura&hasta=").text) == 5


def test_parcial_de_la_tabla_conserva_filtros(client, db_path):
  con_datos(db_path)
  html = client.get("/marcaciones").text
  assert 'hx-get="/marcaciones/tabla?"' in html  # sin filtros: sigue siendo "hoy"
  html = client.get("/marcaciones?desde=2026-10-11&hasta=2026-10-11&pin=8").text
  assert 'hx-get="/marcaciones/tabla?desde=2026-10-11&amp;hasta=2026-10-11&amp;pin=8"' in html
  parcial = client.get("/marcaciones/tabla?desde=2026-10-11&hasta=2026-10-11&pin=8").text
  assert "<html" not in parcial and 'id="tabla-marcaciones"' in parcial
  assert filas_en(parcial) == 1 and "2026-10-11 09:00:00" in parcial


def test_aviso_si_se_corta_el_limite(client, db_path, monkeypatch):
  monkeypatch.setattr(panel, "LIMITE_FILAS", 3)
  con_datos(db_path)
  html = client.get("/marcaciones?desde=&hasta=").text
  assert filas_en(html) == 3 and "más nuevas" in html
  assert "más nuevas" not in client.get("/marcaciones?desde=&hasta=&pin=7").text


def test_se_escapa_el_html(client, db_path):
  db.upsert_empleados(SN, parse_users("USER PIN=5\tName=<script>alert(1)</script>\tPri=0\n"), db_path)
  cargar(db_path, [marcacion(5, "2026-10-11 08:00:00")])
  for url in ("/marcaciones?desde=&hasta=", "/empleados"):
    html = client.get(url).text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_empleados_lista_con_cantidad_de_marcaciones(client, db_path):
  con_datos(db_path)
  cargar(db_path, [marcacion(7, "2026-10-12 08:00:00")])  # Ana: 3 marcaciones; Luis: 2
  html = client.get("/empleados").text
  assert filas_en(html) == 2
  assert "Ana Gómez" in html and "Luis Pérez" in html
  assert "<td>1234567</td>" in html  # tarjeta de Luis
  assert "<td>3</td>" in html and "<td>2</td>" in html
  assert "Passwd" not in html and "4821" not in html


def test_empleados_vacio(client, db_path):
  assert "Todavía no se recibieron empleados" in client.get("/empleados").text


def test_static_local(client):
  r = client.get("/static/htmx.min.js")
  assert r.status_code == 200 and "htmx" in r.text
  assert client.get("/static/style.css").status_code == 200
  assert client.get("/static/no_existe.js").status_code == 404


def test_panel_rechaza_clientes_no_locales(client_externo, db_path):
  for url in ("/", "/marcaciones", "/marcaciones/tabla", "/empleados",
              "/static/htmx.min.js", "/static/style.css"):
    assert client_externo.get(url, follow_redirects=False).status_code == 403, url
  assert not db_path.exists()


def test_iclock_sigue_funcionando_desde_la_red(client_externo, db_path):
  r = client_externo.get("/iclock/getrequest?SN=TESTSN0001")
  assert (r.status_code, r.text) == (200, "OK")
  r = client_externo.post(f"/iclock/cdata?SN={SN}&table=OPERLOG&OpStamp=1",
                          content=fixture_text("operlog_usuarios.txt"))
  assert (r.status_code, r.text) == (200, "OK")
  r = client_externo.post(f"/iclock/cdata?SN={SN}&table=ATTLOG&Stamp=1",
                          content=fixture_text("attlog_tiempo_real.txt"))
  assert (r.status_code, r.text) == (200, "OK")


def test_ruta_desconocida_la_captura_el_espia_incluso_desde_la_red(client_externo):
  r = client_externo.get("/algo/raro")
  assert (r.status_code, r.text) == (200, "OK")
