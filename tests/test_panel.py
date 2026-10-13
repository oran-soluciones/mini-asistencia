import re
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


def celda(html, texto):
  """True si hay una <td> (con o sin atributos) con exactamente ese texto."""
  return re.search(rf"<td(?:\s[^>]*)?>\s*{re.escape(texto)}\s*</td>", html) is not None


def test_raiz_redirige_a_hoy(client):
  r = client.get("/", follow_redirects=False)
  assert r.status_code in (302, 307)
  assert r.headers["location"] == "/hoy"


def test_marcaciones_muestra_filas_nombre_y_verificacion(client, db_path):
  con_datos(db_path)
  html = client.get("/marcaciones?desde=&hasta=").text
  assert "mini-asistencia" in html
  assert celda(html, "11/10/2026") and celda(html, "08:01:00") and celda(html, "Ana Gómez")
  assert filas_en(html) == 5
  assert "Cara" in html and "no verificado" in html  # verificación 15
  assert celda(html, "1")  # verificación 1 se muestra como número
  # Más nueva primero
  assert html.index("12/10/2026") < html.index("10/10/2026")
  # El PIN sin empleado se muestra igual, con el nombre vacío
  assert re.search(r'<td class="num">99</td>\s*<td></td>', html)


def test_marcaciones_por_defecto_muestra_hoy(client, db_path):
  hoy = date.today().isoformat()
  cargar(db_path, [marcacion(7, f"{hoy} 07:30:00"), marcacion(7, "2026-01-01 07:30:00")])
  html = client.get("/marcaciones").text
  assert celda(html, date.today().strftime("%d/%m/%Y")) and "01/01/2026" not in html
  assert f'value="{hoy}"' in html


def test_filtro_desde_hasta_inclusivo(client, db_path):
  con_datos(db_path)
  html = client.get("/marcaciones?desde=2026-10-11&hasta=2026-10-11").text
  assert filas_en(html) == 2
  assert celda(html, "08:01:00") and celda(html, "09:00:00")
  assert filas_en(client.get("/marcaciones?desde=2026-10-12&hasta=").text) == 2
  assert filas_en(client.get("/marcaciones?desde=&hasta=2026-10-10").text) == 1


def test_filtro_por_pin(client, db_path):
  con_datos(db_path)
  html = client.get("/marcaciones?desde=&hasta=&pin=8").text
  assert filas_en(html) == 2 and "Luis Pérez" in html
  assert not celda(html, "Ana Gómez")
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
  assert filas_en(parcial) == 1 and celda(parcial, "09:00:00")


def test_aviso_si_se_corta_el_limite(client, db_path, monkeypatch):
  monkeypatch.setattr(panel, "LIMITE_FILAS", 3)
  con_datos(db_path)
  html = client.get("/marcaciones?desde=&hasta=").text
  assert filas_en(html) == 3 and "más nuevas" in html
  assert "más nuevas" not in client.get("/marcaciones?desde=&hasta=&pin=7").text


def tipos_de(html):
  """Tipos de la columna Tipo, en el orden en que salen en la tabla."""
  return re.findall(r'<span class="tipo tipo-[a-z]+">([A-Za-z]+)</span>', html)


def test_columna_tipo_usa_la_regla_de_la_jornada(client, db_path):
  # Más nueva primero: 17:00 salida, 12:00 intermedia, 08:01 repetida, 08:00 entrada
  cargar(db_path, [
    marcacion(7, "2026-10-12 08:00:00"), marcacion(7, "2026-10-12 08:01:30"),
    marcacion(7, "2026-10-12 12:00:00"), marcacion(7, "2026-10-12 17:00:00"),
    marcacion(8, "2026-10-12 09:00:00"),  # una sola: queda como entrada
  ])
  html = client.get("/marcaciones?desde=&hasta=").text
  por_hora = dict(zip(re.findall(r'<td class="num">(\d\d:\d\d:\d\d)</td>', html), tipos_de(html)))
  assert por_hora == {"17:00:00": "Salida", "12:00:00": "Intermedia", "08:01:30": "Repetida",
                      "08:00:00": "Entrada", "09:00:00": "Entrada"}
  assert "tipo-repetida" in html


def test_columna_tipo_cada_dia_por_separado(client, db_path):
  cargar(db_path, [marcacion(7, "2026-10-11 08:00:00"), marcacion(7, "2026-10-12 08:00:00")])
  html = client.get("/marcaciones?desde=&hasta=").text
  assert tipos_de(html) == ["Entrada", "Entrada"]


def test_columna_tipo_se_omite_en_el_dia_cortado_por_el_limite(client, db_path, monkeypatch):
  monkeypatch.setattr(panel, "LIMITE_FILAS", 3)
  cargar(db_path, [
    marcacion(7, "2026-10-11 08:00:00"), marcacion(7, "2026-10-11 17:00:00"),
    marcacion(7, "2026-10-12 08:00:00"), marcacion(7, "2026-10-12 17:00:00"),
  ])
  html = client.get("/marcaciones?desde=&hasta=").text
  # El 11 quedó con una sola fila visible: su Tipo sería engañoso, no se muestra
  assert tipos_de(html) == ["Salida", "Entrada"]


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
  assert celda(html, "1234567")  # tarjeta de Luis
  assert celda(html, "3") and celda(html, "2")
  assert "Passwd" not in html and "4821" not in html


def test_empleados_vacio(client, db_path):
  assert "Todavía no se recibieron empleados" in client.get("/empleados").text


def test_empleados_alta_en_linea_y_comandos_plegables(client, db_path):
  html = client.get("/empleados").text
  assert '<form method="post" action="/empleados" class="alta">' in html
  assert html.index('class="alta"') < html.index('id="tabla-empleados"')  # arriba de la planilla
  assert '<details class="comandos-det">' in html and "Últimos comandos" in html
  assert "<dialog" not in html


def test_static_local(client):
  r = client.get("/static/htmx.min.js")
  assert r.status_code == 200 and "htmx" in r.text
  assert client.get("/static/style.css").status_code == 200
  assert client.get("/static/panel.js").status_code == 200
  assert client.get("/static/iconos.svg").status_code == 200
  assert client.get("/static/no_existe.js").status_code == 404


def test_sin_recursos_externos(client):
  """Sin CDN ni fuentes web: todo lo que carga el panel sale de /static."""
  for url in ("/hoy", "/marcaciones", "/empleados", "/configuracion"):
    html = client.get(url).text
    assert not re.search(r'(?:src|href)="https?://', html), url
  css = client.get("/static/style.css").text
  assert "@import" not in css and "http://" not in css.replace("http://www.w3.org", "")


def test_panel_rechaza_clientes_no_locales(client_externo, db_path):
  for url in ("/", "/hoy", "/hoy/tabla", "/reloj", "/marcaciones", "/marcaciones/tabla",
              "/empleados", "/configuracion", "/colegio/logo",
              "/static/htmx.min.js", "/static/style.css", "/static/panel.js"):
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
