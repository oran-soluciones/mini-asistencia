from io import BytesIO

import pytest
from PIL import Image

from app import colegio, config, panel

NOMBRE = "E.E.T. N° 8.102 San José Obrero"


def imagen(formato="PNG", tamano=(120, 120)):
  buffer = BytesIO()
  Image.new("RGB", tamano, (20, 90, 60)).save(buffer, format=formato)
  return buffer.getvalue()


SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>'


def guardar(client, nombre=NOMBRE, logo=None, **kwargs):
  archivos = {"logo": logo} if logo else None
  return client.post("/configuracion", data={"nombre": nombre}, files=archivos,
                     follow_redirects=False, **kwargs)


def datos():
  return config.DATA_DIR


def test_pagina_de_configuracion_vacia(client):
  r = client.get("/configuracion")
  assert r.status_code == 200
  assert 'name="nombre"' in r.text and 'name="logo"' in r.text and 'enctype="multipart/form-data"' in r.text
  assert "Quitar logo" not in r.text and "Sin logo" in r.text


def test_barra_pide_cargar_nombre_y_logo_si_faltan(client):
  html = client.get("/hoy").text
  assert 'href="/configuracion">Cargá el nombre y el logo del colegio</a>' in html
  assert "marca-vacia" in html and "marca-disco" not in html


def test_guardar_nombre(client):
  r = guardar(client)
  assert (r.status_code, r.headers["location"]) == (303, "/configuracion?guardado=1")
  assert colegio.leer() == {"nombre": NOMBRE, "logo": None}
  assert (datos() / "colegio.json").is_file()
  html = client.get("/configuracion?guardado=1").text
  assert "Guardado." in html and f'value="{NOMBRE}"' in html
  barra = client.get("/hoy").text
  assert f'<span class="marca-nombre">{NOMBRE}</span>' in barra
  assert "Cargá el nombre y el logo" not in barra and "Cargá el logo del colegio" in barra


def test_nombre_se_recorta_y_se_escapa(client):
  guardar(client, "  <b>Escuela</b>  ")
  assert colegio.leer()["nombre"] == "<b>Escuela</b>"
  html = client.get("/marcaciones").text
  assert "&lt;b&gt;Escuela&lt;/b&gt;" in html and "<b>Escuela</b>" not in html


def test_nombre_vacio_vuelve_al_estado_vacio(client):
  guardar(client)
  guardar(client, "")
  assert colegio.leer()["nombre"] == ""
  assert "Cargá el nombre y el logo del colegio" in client.get("/hoy").text


def test_nombre_demasiado_largo_no_se_guarda(client):
  guardar(client, "Colegio Nacional")
  r = guardar(client, "x" * 81)
  assert r.status_code == 400 and "hasta 80 caracteres (tiene 81)" in r.text
  assert colegio.leer()["nombre"] == "Colegio Nacional"
  assert guardar(client, "x" * 80).status_code == 303


def test_nombre_con_caracteres_de_control(client):
  r = guardar(client, "Colegio\x07")
  assert r.status_code == 400 and "caracteres de control" in r.text


@pytest.mark.parametrize("formato,ext,mime", [("PNG", "png", "image/png"), ("JPEG", "jpg", "image/jpeg")])
def test_logo_valido_se_guarda_y_se_sirve(client, formato, ext, mime):
  contenido = imagen(formato)
  r = guardar(client, logo=("logo.bin", contenido, "application/octet-stream"))
  assert r.status_code == 303
  assert (datos() / f"logo.{ext}").read_bytes() == contenido
  assert colegio.leer()["logo"] == f"logo.{ext}" and colegio.tipo_logo() == mime
  r = client.get("/colegio/logo")
  assert r.status_code == 200 and r.headers["content-type"] == mime and r.content == contenido
  assert r.headers["x-content-type-options"] == "nosniff"
  assert "sandbox" in r.headers["content-security-policy"]
  barra = client.get("/hoy").text
  assert '<span class="marca-disco"><img src="/colegio/logo?v=' in barra
  assert "marca-vacia" not in barra
  assert "Quitar logo" in client.get("/configuracion").text


def test_logo_svg_valido(client):
  assert guardar(client, logo=("logo.svg", SVG, "image/svg+xml")).status_code == 303
  r = client.get("/colegio/logo")
  assert r.headers["content-type"] == "image/svg+xml" and r.content == SVG


def test_el_tipo_se_decide_por_el_contenido_no_por_el_nombre(client):
  guardar(client, logo=("foto.svg", imagen("PNG"), "image/svg+xml"))
  assert colegio.leer()["logo"] == "logo.png"
  r = guardar(client, logo=("logo.png", b"<html><body>hola</body></html>", "image/png"))
  assert r.status_code == 400 and "PNG, JPG o SVG" in r.text
  r = guardar(client, logo=("logo.png", b"\x89PNG\r\n\x1a\nbasura", "image/png"))
  assert r.status_code == 400 and "dañada" in r.text
  assert colegio.leer()["logo"] == "logo.png"  # el anterior sigue ahí


def test_logo_demasiado_grande_se_rechaza_y_no_guarda_nada(client):
  grande = imagen("PNG") + b"\0" * colegio.LOGO_MAX_BYTES  # válido pero pasa de 1 MB
  assert len(grande) > colegio.LOGO_MAX_BYTES
  r = guardar(client, "Nombre nuevo", logo=("logo.png", grande, "image/png"))
  assert r.status_code == 400 and "1 MB" in r.text
  assert colegio.leer() == {"nombre": "", "logo": None}  # ni el nombre se guardó
  assert not list(datos().glob("logo.*")) and 'value="Nombre nuevo"' in r.text


def test_logo_justo_en_el_limite_se_acepta(client):
  base = imagen("PNG")
  # un PNG con relleno después del final sigue siendo legible: llega a 1 MB exacto
  justo = base + b"\0" * (colegio.LOGO_MAX_BYTES - len(base))
  assert len(justo) == colegio.LOGO_MAX_BYTES
  assert guardar(client, logo=("logo.png", justo, "image/png")).status_code == 303


@pytest.mark.parametrize("malicioso", [
  b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
  b'<svg xmlns="http://www.w3.org/2000/svg"><SCRIPT >alert(1)</SCRIPT></svg>',
  b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
  b'<svg xmlns="http://www.w3.org/2000/svg"><rect onclick = "x()"/></svg>',
  b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
  b'<a href="javascript:alert(1)"><rect/></a></svg>',
  b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><div>x</div></foreignObject></svg>',
])
def test_svg_con_codigo_activo_se_rechaza(client, malicioso):
  r = guardar(client, logo=("logo.svg", malicioso, "image/svg+xml"))
  assert r.status_code == 400 and "código activo" in r.text
  assert colegio.leer() == {"nombre": "", "logo": None}
  assert not list(datos().glob("logo.*"))


def test_cambiar_de_formato_borra_el_logo_anterior(client):
  guardar(client, logo=("a.png", imagen("PNG"), "image/png"))
  guardar(client, logo=("a.svg", SVG, "image/svg+xml"))
  assert [p.name for p in datos().glob("logo.*")] == ["logo.svg"]
  assert colegio.leer()["logo"] == "logo.svg"


def test_guardar_sin_elegir_archivo_conserva_el_logo(client):
  guardar(client, logo=("a.png", imagen("PNG"), "image/png"))
  r = guardar(client, "Otro nombre", logo=("", b"", "application/octet-stream"))  # campo vacío
  assert r.status_code == 303
  assert colegio.leer() == {"nombre": "Otro nombre", "logo": "logo.png"}
  guardar(client, "Y otro")  # sin el campo siquiera
  assert colegio.leer() == {"nombre": "Y otro", "logo": "logo.png"}


def test_quitar_logo_conserva_el_nombre(client):
  guardar(client, logo=("a.png", imagen("PNG"), "image/png"))
  r = client.post("/configuracion/logo/quitar", follow_redirects=False)
  assert (r.status_code, r.headers["location"]) == (303, "/configuracion?guardado=1")
  assert colegio.leer() == {"nombre": NOMBRE, "logo": None}
  assert not list(datos().glob("logo.*"))
  assert client.get("/colegio/logo").status_code == 404
  assert "Quitar logo" not in client.get("/configuracion").text
  assert client.post("/configuracion/logo/quitar", follow_redirects=False).status_code == 303  # sin logo: no falla


def test_archivo_de_configuracion_danado_no_rompe_el_panel(client):
  (datos() / "colegio.json").write_text("{esto no es json", encoding="utf-8")
  assert client.get("/hoy").status_code == 200 and client.get("/configuracion").status_code == 200
  (datos() / "colegio.json").write_text('{"nombre": 5, "logo": "../../etc/passwd"}', encoding="utf-8")
  assert colegio.leer() == {"nombre": "", "logo": None}


def test_el_logo_guardado_no_puede_apuntar_fuera_de_la_carpeta(client):
  (datos() / "colegio.json").write_text('{"nombre": "X", "logo": "colegio.json"}', encoding="utf-8")
  assert colegio.leer()["logo"] is None and client.get("/colegio/logo").status_code == 404


# --- Seguridad -----------------------------------------------------------------------------

MALOS = [
  {"origin": "http://evil.example"},
  {"origin": "null"},
  {"origin": f"http://localhost:{panel.PORT + 1}"},
  {"referer": "http://evil.example/pagina"},
]


@pytest.mark.parametrize("headers", MALOS)
def test_csrf_en_configuracion_da_403(client, headers):
  r = guardar(client, "Hackeado", logo=("a.png", imagen("PNG"), "image/png"), headers=headers)
  assert r.status_code == 403
  assert colegio.leer() == {"nombre": "", "logo": None} and not list(datos().glob("logo.*"))


@pytest.mark.parametrize("headers", MALOS)
def test_csrf_al_quitar_el_logo_da_403(client, headers):
  guardar(client, logo=("a.png", imagen("PNG"), "image/png"))
  assert client.post("/configuracion/logo/quitar", headers=headers).status_code == 403
  assert colegio.leer()["logo"] == "logo.png"


def test_origen_propio_se_acepta(client):
  r = guardar(client, headers={"origin": f"http://localhost:{panel.PORT}"})
  assert r.status_code == 303


def test_configuracion_desde_la_red_da_403(client_externo):
  assert client_externo.get("/configuracion").status_code == 403
  assert client_externo.get("/colegio/logo").status_code == 403
  r = client_externo.post("/configuracion", data={"nombre": "x"})
  assert r.status_code == 403
  assert client_externo.post("/configuracion/logo/quitar").status_code == 403
  assert colegio.leer()["nombre"] == ""


def test_configuracion_explica_como_conectar_el_reloj(client, db_path, monkeypatch):
  monkeypatch.setattr(panel, "ips_locales", lambda: ["192.168.1.50", "10.0.0.7"])
  html = client.get("/configuracion").text
  assert "Conectar el reloj" in html
  assert '<span class="valor num">192.168.1.50</span>' in html and "10.0.0.7" in html
  assert f'<span class="valor num">{panel.PORT}</span>' in html
  assert f"localport={panel.PORT}" in html and f"findstr :{panel.PORT}" in html
  assert "data-copiar=" in html and "Todavía no se conectó" in html


def test_configuracion_sin_red_lo_avisa(client, db_path, monkeypatch):
  monkeypatch.setattr(panel, "ips_locales", lambda: [])
  assert "No se encontró" in client.get("/configuracion").text


def test_ips_locales_sin_loopback():
  ips = panel.ips_locales()
  assert all(not ip.startswith(("127.", "169.254.")) for ip in ips) and len(ips) == len(set(ips))
