from contextlib import closing
from datetime import datetime, timedelta

import re

import pytest

from app import db, panel
from app.iclock import comando_baja, comando_usuario, parse_devicecmd, parse_users

SN = "TESTSN0001"
OTRO_SN = "TESTSN0002"
GETREQUEST = f"/iclock/getrequest?SN={SN}"
DEVICECMD = f"/iclock/devicecmd?SN={SN}"


class Reloj:
  """Hora de la PC controlable (reemplaza db.ahora)."""

  def __init__(self):
    self.t = datetime(2026, 10, 13, 12, 0, 0)

  def avanzar(self, segundos):
    self.t += timedelta(seconds=segundos)


@pytest.fixture
def hora(monkeypatch):
  reloj = Reloj()
  monkeypatch.setattr(db, "ahora", lambda: reloj.t)
  return reloj


def comandos(path):
  with closing(db.connect(path)) as conn:
    return conn.execute("SELECT * FROM comandos ORDER BY id").fetchall()


def empleados(path):
  with closing(db.connect(path)) as conn:
    return conn.execute("SELECT * FROM empleados ORDER BY pin").fetchall()


def alta(client, pin="99", nombre="Prueba", privilegio="0", **kwargs):
  return client.post("/empleados", data={"pin": pin, "nombre": nombre, "privilegio": privilegio},
                     follow_redirects=False, **kwargs)


def confirmar(client, cmd_id, codigo=0, sn=SN):
  return client.post(f"/iclock/devicecmd?SN={sn}", content=f"ID={cmd_id}&Return={codigo}&CMD=DATA")


def con_reloj(client):
  """El reloj ya hizo su primer getrequest (el panel lo necesita para saber el SN destino)."""
  assert client.get(GETREQUEST).text == "OK"


# --- formato de los comandos -------------------------------------------------------------

def test_formato_comando_alta():
  assert comando_usuario("99", "Prueba", 0) == (
    "DATA UPDATE USERINFO PIN=99\tName=Prueba\tPri=0\tPasswd=\tCard=\tGrp=1"
    "\tTZ=0000000000000000\tVerify=0\tViceCard=\tStartDatetime=0\tEndDatetime=0")
  assert comando_usuario("5", "Ana", 14, "1234567", 2) == (
    "DATA UPDATE USERINFO PIN=5\tName=Ana\tPri=14\tPasswd=\tCard=1234567\tGrp=2"
    "\tTZ=0000000000000000\tVerify=0\tViceCard=\tStartDatetime=0\tEndDatetime=0")


def test_formato_comando_baja():
  assert comando_baja("99") == "DATA DELETE USERINFO PIN=99"


# --- getrequest / relojes ------------------------------------------------------------------

def test_getrequest_sin_comandos_responde_ok_y_registra_el_reloj(client, db_path, hora):
  assert db.ultimo_reloj(db_path) is None
  r = client.get(GETREQUEST)
  assert (r.status_code, r.text) == (200, "OK")
  reloj = db.ultimo_reloj(db_path)
  assert (reloj["sn"], reloj["ultimo_contacto"]) == (SN, "2026-10-13 12:00:00")
  hora.avanzar(5)
  client.get(GETREQUEST)
  assert db.ultimo_reloj(db_path)["ultimo_contacto"] == "2026-10-13 12:00:05"


def test_ultimo_reloj_es_el_ultimo_en_hablar(client, db_path, hora):
  client.get(GETREQUEST)
  hora.avanzar(3)
  client.get(f"/iclock/getrequest?SN={OTRO_SN}")
  assert db.ultimo_reloj(db_path)["sn"] == OTRO_SN


def test_getrequest_sin_sn_no_rompe(client, db_path):
  r = client.get("/iclock/getrequest")
  assert (r.status_code, r.text) == (200, "OK")
  assert db.ultimo_reloj(db_path) is None


def test_getrequest_entrega_el_comando_y_no_lo_repite_hasta_el_reintento(client, db_path, hora):
  con_reloj(client)
  assert alta(client).status_code == 303
  r = client.get(GETREQUEST)
  assert r.status_code == 200
  assert r.text == "C:1:" + comando_usuario("99", "Prueba", 0) + "\n"
  assert "\t" in r.text and r.text.endswith("\n")
  c = comandos(db_path)[0]
  assert (c["estado"], c["intentos"], c["enviado"]) == ("enviado", 1, "2026-10-13 12:00:00")
  # Dentro de los 2 minutos no se repite
  hora.avanzar(119)
  assert client.get(GETREQUEST).text == "OK"
  assert comandos(db_path)[0]["intentos"] == 1
  # Pasados los 2 minutos sin confirmación se reentrega
  hora.avanzar(2)
  r = client.get(GETREQUEST)
  assert r.text.startswith("C:1:DATA UPDATE USERINFO PIN=99")
  c = comandos(db_path)[0]
  assert (c["estado"], c["intentos"]) == ("enviado", 2)


def test_tras_max_entregas_sin_confirmar_pasa_a_error(client, db_path, hora):
  con_reloj(client)
  alta(client)
  for _ in range(db.MAX_ENTREGAS):
    assert client.get(GETREQUEST).text.startswith("C:1:")
    hora.avanzar(db.REINTENTO_SEGUNDOS + 1)
  assert client.get(GETREQUEST).text == "OK"
  c = comandos(db_path)[0]
  assert (c["estado"], c["codigo_retorno"], c["intentos"]) == ("error", None, db.MAX_ENTREGAS)
  assert "Error (sin respuesta)" in client.get("/empleados").text
  # Una confirmación tardía todavía se acepta
  assert confirmar(client, 1).text == "OK"
  assert comandos(db_path)[0]["estado"] == "ok"


def test_un_comando_por_vez_y_en_orden(client, db_path, hora):
  con_reloj(client)
  alta(client, "98", "Uno")
  alta(client, "99", "Dos")
  assert client.get(GETREQUEST).text.startswith("C:1:")
  assert client.get(GETREQUEST).text == "OK"  # el 1 sigue sin confirmar: el 2 espera
  confirmar(client, 1)
  assert client.get(GETREQUEST).text.startswith("C:2:")
  assert client.get(GETREQUEST).text == "OK"


def test_comando_de_otro_sn_no_se_entrega(client, db_path, hora):
  con_reloj(client)
  alta(client)
  assert client.get(f"/iclock/getrequest?SN={OTRO_SN}").text == "OK"
  assert comandos(db_path)[0]["estado"] == "pendiente"
  assert client.get(GETREQUEST).text.startswith("C:1:")


def test_nombre_con_tildes_se_envia_en_utf8(client, db_path):
  con_reloj(client)
  alta(client, "99", "Muñoz Ángel")
  r = client.get(GETREQUEST)
  assert "Name=Muñoz Ángel\t" in r.content.decode("utf-8")
  assert "utf-8" in r.headers["content-type"].lower()


# --- devicecmd -------------------------------------------------------------------------------

def test_parse_devicecmd_tolerante():
  assert parse_devicecmd("ID=12&Return=0&CMD=DATA") == [(12, 0)]
  assert parse_devicecmd("CMD=DATA&Return=-1&ID=3\r\nid=4&RETURN=0\n\n") == [(3, -1), (4, 0)]
  assert parse_devicecmd("") == []
  assert parse_devicecmd("basura\nID=x&Return=0\nID=1\n&&=\x00\xff") == []


def test_devicecmd_return_0_confirma(client, db_path, hora):
  con_reloj(client)
  alta(client)
  client.get(GETREQUEST)
  hora.avanzar(2)
  r = confirmar(client, 1)
  assert (r.status_code, r.text) == (200, "OK")
  c = comandos(db_path)[0]
  assert (c["estado"], c["codigo_retorno"], c["confirmado"]) == ("ok", 0, "2026-10-13 12:00:02")
  assert [e["pin"] for e in empleados(db_path)] == ["99"]  # el alta no borra nada
  assert client.get(GETREQUEST).text == "OK"


def test_devicecmd_return_distinto_de_0_es_error_con_codigo(client, db_path):
  con_reloj(client)
  alta(client)
  client.get(GETREQUEST)
  confirmar(client, 1, -2)
  c = comandos(db_path)[0]
  assert (c["estado"], c["codigo_retorno"]) == ("error", -2)
  assert "Error (código -2)" in client.get("/empleados").text
  assert client.get(GETREQUEST).text == "OK"  # no se reintenta solo un error del reloj


def test_devicecmd_varias_lineas(client, db_path):
  con_reloj(client)
  alta(client, "98", "Uno")
  alta(client, "99", "Dos")
  client.get(GETREQUEST)
  confirmar(client, 1)
  client.get(GETREQUEST)
  r = client.post(DEVICECMD, content="ID=1&Return=0&CMD=DATA\nCMD=DATA&Return=7&ID=2\n")
  assert r.text == "OK"
  assert [(c["estado"], c["codigo_retorno"]) for c in comandos(db_path)] == [("ok", 0), ("error", 7)]


@pytest.mark.parametrize("body", [
  "", "basura", "ID=&Return=", "ID=999&Return=0&CMD=DATA", "\x00\xff\xfe=&&", "ID=1",
])
def test_devicecmd_body_raro_no_rompe(client, db_path, body):
  con_reloj(client)
  alta(client)
  client.get(GETREQUEST)
  r = client.post(DEVICECMD, content=body.encode("latin-1"))
  assert (r.status_code, r.text) == (200, "OK")
  assert comandos(db_path)[0]["estado"] == "enviado"


def test_devicecmd_repetido_no_cambia_nada(client, db_path):
  con_reloj(client)
  alta(client)
  client.get(GETREQUEST)
  confirmar(client, 1, 0)
  confirmar(client, 1, 5)  # ya estaba confirmado
  assert comandos(db_path)[0]["codigo_retorno"] == 0


def test_requests_del_reloj_se_guardan_en_samples(client, tmp_path):
  client.get(GETREQUEST)
  confirmar(client, 1)
  nombres = [f.name for f in tmp_path.glob("*.txt")]
  assert any("GET_iclock_getrequest" in n for n in nombres)
  assert any("POST_iclock_devicecmd" in n for n in nombres)


# --- alta / modificación / baja desde el panel ----------------------------------------------

def test_alta_crea_empleado_local_y_encola(client, db_path):
  con_reloj(client)
  r = alta(client, " 99 ", "  Prueba  ", "14")
  assert (r.status_code, r.headers["location"]) == (303, "/empleados")
  e = empleados(db_path)[0]
  assert (e["pin"], e["nombre"], e["privilegio"], e["sn"], e["grupo"]) == ("99", "Prueba", 14, SN, 1)
  c = comandos(db_path)[0]
  assert (c["sn"], c["pin"], c["tipo"], c["estado"]) == (SN, "99", "alta", "pendiente")
  assert c["texto"] == comando_usuario("99", "Prueba", 14)


def test_alta_sin_reloj_conocido_da_error(client, db_path):
  r = alta(client)
  assert r.status_code == 409 and "no se conectó ningún reloj" in r.text
  assert empleados(db_path) == [] and comandos(db_path) == []


def test_alta_con_pin_existente_da_error(client, db_path):
  con_reloj(client)
  db.upsert_empleados(SN, parse_users("USER PIN=99\tName=Ya\tPri=0\n"), db_path)
  r = alta(client, "99", "Otro")
  assert r.status_code == 409 and "Ya existe un empleado con PIN 99" in r.text
  assert empleados(db_path)[0]["nombre"] == "Ya" and comandos(db_path) == []


@pytest.mark.parametrize("pin", ["", "007", "0", "abc", "12a", "1234567890", "-5", "1 2", "٣"])
def test_alta_pin_invalido(client, db_path, pin):
  con_reloj(client)
  r = alta(client, pin, "Prueba")
  assert r.status_code == 400 and "El PIN debe ser" in r.text
  assert empleados(db_path) == [] and comandos(db_path) == []


@pytest.mark.parametrize("pin", ["1", "7", "99", "123456789"])
def test_alta_pin_valido(client, db_path, pin):
  con_reloj(client)
  assert alta(client, pin).status_code == 303


@pytest.mark.parametrize("nombre,mensaje", [
  ("", "obligatorio"), ("   ", "obligatorio"), ("x" * 25, "hasta 24"),
  ("Ana\tPérez", "tabulaciones"), ("Ana\nPérez", "saltos de línea"), ("Ana\rPérez", "saltos de línea"),
])
def test_alta_nombre_invalido(client, db_path, nombre, mensaje):
  con_reloj(client)
  r = alta(client, "99", nombre)
  assert r.status_code == 400 and mensaje in r.text
  assert comandos(db_path) == []


def test_alta_nombre_24_caracteres_y_tildes_ok(client, db_path):
  con_reloj(client)
  assert alta(client, "99", "ñ" * 24).status_code == 303
  assert alta(client, "98", "Ángel Muñoz").status_code == 303


def test_alta_privilegio_invalido(client, db_path):
  con_reloj(client)
  for valor in ("7", "x", "15"):
    r = alta(client, "99", "Prueba", valor)
    assert r.status_code == 400 and "privilegio" in r.text
  assert comandos(db_path) == []


def test_error_de_alta_conserva_lo_escrito_y_escapa(client):
  con_reloj(client)
  r = alta(client, "007", "<b>Ana</b>")
  assert 'value="007"' in r.text and "&lt;b&gt;Ana&lt;/b&gt;" in r.text and "<b>Ana</b>" not in r.text


def test_formulario_ya_no_avisa_de_tildes_no_verificadas(client):
  html = client.get("/empleados").text
  assert "no verificado cómo las muestra" not in html


def test_modificacion_actualiza_local_y_encola_con_tarjeta_y_grupo(client, db_path):
  con_reloj(client)
  db.upsert_empleados(SN, parse_users("USER PIN=7\tName=Ana\tPri=0\tPasswd=4821\tCard=555\tGrp=3\n"), db_path)
  html = client.get("/empleados/7/editar").text
  assert "conserva la cara registrada" not in html and "no verificado" not in html.lower()
  assert "podrían borrarse; todavía no lo comprobamos" in html
  r = client.post("/empleados/7/editar", data={"nombre": "Ana Díaz", "privilegio": "0"},
                  follow_redirects=False)
  assert r.status_code == 303
  assert empleados(db_path)[0]["nombre"] == "Ana Díaz"
  c = comandos(db_path)[0]
  assert (c["tipo"], c["sn"], c["estado"]) == ("modificacion", SN, "pendiente")
  assert c["texto"] == comando_usuario("7", "Ana Díaz", 0, "555", 3)
  assert "4821" not in c["texto"]


def test_modificacion_valida_el_nombre(client, db_path):
  con_reloj(client)
  db.upsert_empleados(SN, parse_users("USER PIN=7\tName=Ana\tPri=0\n"), db_path)
  r = client.post("/empleados/7/editar", data={"nombre": "", "privilegio": "0"})
  assert r.status_code == 400 and "obligatorio" in r.text
  assert comandos(db_path) == []


def test_baja_encola_y_borra_la_fila_recien_al_confirmar(client, db_path):
  con_reloj(client)
  alta(client)
  client.get(GETREQUEST)
  confirmar(client, 1)
  r = client.post("/empleados/99/baja", follow_redirects=False)
  assert (r.status_code, r.headers["location"]) == (303, "/empleados")
  c = comandos(db_path)[1]
  assert (c["tipo"], c["texto"], c["estado"]) == ("baja", "DATA DELETE USERINFO PIN=99", "pendiente")
  # Mientras tanto: sigue en la lista, como baja pendiente y sin botones
  html = client.get("/empleados").text
  assert "Baja pendiente" in html and 'action="/empleados/99/baja"' not in html
  assert client.post("/empleados/99/baja").status_code == 409
  assert client.get("/empleados/99/editar").status_code == 409
  # El reloj recibe el comando y confirma
  assert client.get(GETREQUEST).text == "C:2:DATA DELETE USERINFO PIN=99\n"
  assert len(empleados(db_path)) == 1
  confirmar(client, 2)
  assert empleados(db_path) == []
  assert comandos(db_path)[1]["estado"] == "ok"


def test_baja_con_error_del_reloj_no_borra_la_fila(client, db_path):
  con_reloj(client)
  alta(client)
  client.get(GETREQUEST)
  confirmar(client, 1)
  client.post("/empleados/99/baja")
  client.get(GETREQUEST)
  confirmar(client, 2, -1)
  assert [e["pin"] for e in empleados(db_path)] == ["99"]
  html = client.get("/empleados").text
  assert "Error (código -1)" in html and 'action="/empleados/99/baja"' in html  # se puede reintentar


def test_baja_o_edicion_de_empleado_inexistente(client):
  assert client.post("/empleados/55/baja").status_code == 404
  assert client.get("/empleados/55/editar").status_code == 404
  assert client.post("/empleados/55/editar", data={"nombre": "x"}).status_code == 404


def test_administrador_protegido(client, db_path):
  con_reloj(client)
  db.upsert_empleados(SN, parse_users("USER PIN=1\tName=Jefe\tPri=14\tPasswd=secreta\n"), db_path)
  html = client.get("/empleados").text
  assert "Administrador: se gestiona en el reloj" in html
  assert "/empleados/1/editar" not in html and "/empleados/1/baja" not in html
  r = client.get("/empleados/1/editar")
  assert r.status_code == 403 and "no se modifican ni se dan de baja" in r.text
  assert client.post("/empleados/1/editar", data={"nombre": "Otro", "privilegio": "0"}).status_code == 403
  assert client.post("/empleados/1/baja").status_code == 403
  assert comandos(db_path) == []
  assert empleados(db_path)[0]["nombre"] == "Jefe"
  assert "secreta" not in html


def test_se_puede_dar_de_alta_un_administrador_pero_despues_queda_protegido(client, db_path):
  con_reloj(client)
  assert alta(client, "50", "Nuevo Admin", "14").status_code == 303
  assert client.post("/empleados/50/baja").status_code == 403


# --- CSRF ---------------------------------------------------------------------------------------

POSTS = [
  ("/empleados", {"pin": "99", "nombre": "Prueba", "privilegio": "0"}),
  ("/empleados/7/editar", {"nombre": "Otro", "privilegio": "0"}),
  ("/empleados/7/baja", {}),
]


@pytest.mark.parametrize("url,data", POSTS)
@pytest.mark.parametrize("headers", [
  {"origin": "http://evil.example"},
  {"origin": "null"},
  {"origin": f"http://localhost:{panel.PORT + 1}"},
  {"origin": f"https://localhost:{panel.PORT}"},
  {"referer": "http://evil.example/pagina"},
  {"referer": f"http://localhost.evil.example:{panel.PORT}/x"},
  {"origin": "http://evil.example", "referer": f"http://localhost:{panel.PORT}/empleados"},
])
def test_csrf_origen_ajeno_da_403(client, db_path, url, data, headers):
  con_reloj(client)
  db.upsert_empleados(SN, parse_users("USER PIN=7\tName=Ana\tPri=0\n"), db_path)
  r = client.post(url, data=data, headers=headers)
  assert r.status_code == 403
  assert comandos(db_path) == []
  assert [e["pin"] for e in empleados(db_path)] == ["7"]


@pytest.mark.parametrize("headers", [
  {},
  {"origin": f"http://localhost:{panel.PORT}"},
  {"origin": f"http://127.0.0.1:{panel.PORT}"},
  {"referer": f"http://localhost:{panel.PORT}/empleados"},
])
def test_csrf_origen_propio_o_sin_origen_se_acepta(client, db_path, headers):
  con_reloj(client)
  r = alta(client, headers=headers)
  assert r.status_code == 303
  assert len(comandos(db_path)) == 1


def test_post_del_panel_desde_la_red_da_403(client_externo, db_path):
  r = client_externo.post("/empleados", data={"pin": "99", "nombre": "x"})
  assert r.status_code == 403 and not db_path.exists()


# --- el panel muestra los estados ----------------------------------------------------------------

def test_panel_muestra_el_estado_de_cada_comando(client, db_path, hora):
  con_reloj(client)
  alta(client, "97", "Pendiente")
  html = client.get("/empleados").text
  assert "alta: Pendiente" in html and 'class="estado est-pendiente"' in html
  client.get(GETREQUEST)
  assert "alta: Enviado" in client.get("/empleados").text
  confirmar(client, 1)
  html = client.get("/empleados").text
  assert "alta: Confirmado" in html and "est-ok" in html
  alta(client, "96", "Falla")
  client.get(GETREQUEST)
  confirmar(client, 2, 3)
  html = client.get("/empleados").text
  assert "alta: Error (código 3)" in html and "est-error" in html


def test_panel_lista_ultimos_comandos_con_limite(client, db_path):
  con_reloj(client)
  html = client.get("/empleados").text
  assert "Todavía no se envió ningún comando" in html
  for n in range(25):
    db.encolar_comando(SN, str(n + 1), "alta", comando_usuario(str(n + 1), "x", 0), db_path)
  html = client.get("/empleados").text
  assert html.count('<tr class="fila-pendiente">') == 20
  assert html.index("<td>25</td>") < html.index("<td>6</td>")  # el más nuevo primero


def test_panel_indicador_del_reloj(client, db_path, hora):
  html = client.get("/empleados").text
  assert "Todavía no se conectó ningún reloj" in html and "reloj nunca" in html
  con_reloj(client)
  hora.avanzar(10)
  html = client.get("/empleados").text
  assert SN in html and "hace 10 s" in html and "reloj conectado" in html
  hora.avanzar(25)  # 35 s sin contacto
  html = client.get("/empleados").text
  assert "hace 35 s" in html and "reloj sin-contacto" in html and "reloj conectado" not in html
  hora.avanzar(600)
  assert "hace 10 min" in client.get("/empleados").text


def test_parcial_de_estado_se_refresca_con_htmx(client, db_path):
  con_reloj(client)
  alta(client)
  html = client.get("/empleados").text
  assert 'hx-get="/empleados/estado"' in html and 'hx-trigger="every 4s"' in html
  assert "hx-swap-oob" not in html  # en la página completa no hace falta
  parcial = client.get("/empleados/estado").text
  assert "<html" not in parcial and 'id="tabla-empleados"' in parcial
  assert 'id="comandos"' in parcial and parcial.count('hx-swap-oob="true"') == 1
  assert 'id="reloj"' not in parcial  # el indicador del reloj se refresca solo, en la barra
  assert "alta: Pendiente" in parcial


def test_indicador_del_reloj_esta_en_todas_las_vistas_y_se_refresca(client, db_path, hora):
  con_reloj(client)
  hora.avanzar(3)
  for url in ("/hoy", "/marcaciones", "/empleados", "/configuracion"):
    html = client.get(url).text
    assert 'hx-get="/reloj"' in html and "Reloj conectado" in html and "hace 3 s" in html, url
  parcial = client.get("/reloj").text
  assert "<html" not in parcial and 'id="reloj"' in parcial and "hace 3 s" in parcial


def test_ultimos_comandos_con_rotulos_humanos(client, db_path, hora):
  con_reloj(client)
  alta(client, "97", "Pendiente")
  client.get(GETREQUEST)
  confirmar(client, 1)
  alta(client, "96", "Falla")
  client.get(GETREQUEST)
  confirmar(client, 2, 3)
  client.post("/empleados/97/editar", data={"nombre": "Otro", "privilegio": "0"})
  html = client.get("/empleados").text
  tabla = html[html.index('class="planilla-tabla comandos"'):]
  for rotulo in ("N.º", "Operación", "Estado", "Intentos"):
    assert f'<th scope="col">{rotulo}</th>' in tabla
  assert "Entregas" not in tabla and "<th scope=\"col\">Tipo</th>" not in tabla
  assert "<td>Alta</td>" in tabla and "<td>Modificación</td>" in tabla
  assert ">Confirmado</span>" in tabla and ">Pendiente</span>" in tabla
  assert ">Error (código 3)</span>" in tabla
  assert not re.search(r"\d{4}-\d\d-\d\d \d\d:\d\d", tabla)  # fechas dd/mm/aaaa


def test_baja_pide_confirmacion(client, db_path):
  con_reloj(client)
  alta(client)
  html = client.get("/empleados").text
  assert 'onsubmit="return confirm(this.dataset.msg)"' in html and "¿Dar de baja" in html


def test_panel_de_comandos_no_expone_passwd(client, db_path):
  con_reloj(client)
  db.upsert_empleados(SN, parse_users("USER PIN=7\tName=Ana\tPri=0\tPasswd=4821\n"), db_path)
  client.post("/empleados/7/editar", data={"nombre": "Ana B", "privilegio": "0"})
  assert "4821" not in client.get("/empleados").text
  assert "4821" not in client.get(GETREQUEST).text
