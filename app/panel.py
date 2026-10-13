"""Panel web: hoy, marcaciones, empleados (con ABM) y configuración. Jinja2 + HTMX.

Solo responde a clientes locales (127.0.0.1 / ::1): el servidor escucha en toda la red
porque el reloj lo necesita, pero el panel no tiene que verse desde afuera. Los POST además
rechazan orígenes ajenos (CSRF: una web abierta en el navegador podría postear a localhost).
"""
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import colegio, db, jornada, reports
from app.config import PORT
from app.iclock import comando_baja, comando_usuario

BASE_DIR = Path(__file__).resolve().parent
LIMITE_FILAS = 500
LIMITE_COMANDOS = 20
LIMITE_HOY = 50_000  # marcaciones de un solo día: nunca se llega
RELOJ_CONECTADO_SEGUNDOS = 30  # último contacto más reciente que esto = reloj conectado
ADMIN = 14  # privilegio de administrador (deducido del único usuario real, no verificado)
PRIVILEGIOS = {0: "Usuario", ADMIN: "Administrador"}
NOMBRE_MAX = 24
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_LOCALES = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
_PIN_RE = re.compile(r"[1-9][0-9]{0,8}")


def etiqueta_estado(estado: str, codigo: int | None) -> str:
  if estado == "ok":
    return "confirmado"
  if estado == "error":
    return f"error (código {codigo})" if codigo is not None else "error (sin respuesta)"
  return estado


def _hace_txt(segundos: int) -> str:
  if segundos < 120:
    return f"{segundos} s"
  if segundos < 7200:
    return f"{segundos // 60} min"
  return f"{segundos // 3600} h"


def estado_reloj() -> dict:
  """Estado del reloj para el indicador de la barra (se arma en cada render)."""
  reloj = db.ultimo_reloj()
  hace = None
  if reloj:
    ultimo = datetime.fromisoformat(reloj["ultimo_contacto"])
    hace = max(0, int((db.ahora() - ultimo).total_seconds()))
  return {
    "reloj": reloj,
    "hace": None if hace is None else _hace_txt(hace),
    "conectado": hace is not None and hace < RELOJ_CONECTADO_SEGUNDOS,
  }


def datos_colegio() -> dict:
  """Nombre y logo para la barra superior: {'nombre', 'logo' (URL o '')}."""
  datos = colegio.leer()
  return {
    "nombre": datos["nombre"],
    "logo": f"/colegio/logo?v={colegio.version_logo()}" if datos["logo"] else "",
  }


templates = Jinja2Templates(directory=BASE_DIR / "templates")  # autoescape activado
templates.env.globals.update(
  etiqueta_estado=etiqueta_estado, PRIVILEGIOS=PRIVILEGIOS, ADMIN=ADMIN,
  estado_reloj=estado_reloj, datos_colegio=datos_colegio, ESTADOS=jornada.ESTADOS,
  fmt_hm=jornada.fmt_hm, fmt_horas=jornada.fmt_horas, MARCAS_HORA=jornada.MARCAS_HORA,
  INICIO_HORA=jornada.INICIO_MIN // 60, ESCALA_HORAS=jornada.ESCALA_MIN // 60,
)


def _es_local(scope) -> bool:
  client = scope.get("client")
  return bool(client) and client[0] in _LOCALES


def solo_localhost(request: Request) -> None:
  if not _es_local(request.scope):
    raise HTTPException(status_code=403, detail="El panel solo está disponible desde esta PC")


def verificar_origen(request: Request) -> None:
  """Anti-CSRF para los POST: Origin (o, si falta, Referer) tiene que ser este mismo panel.

  Si no viene ninguno de los dos se acepta (clientes que no son navegadores, tests).
  """
  permitidos = {f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"}
  origen = request.headers.get("origin")
  if origen is None:
    referer = request.headers.get("referer")
    if referer is None:
      return
    partes = urlsplit(referer)
    origen = f"{partes.scheme}://{partes.netloc}"
  if origen not in permitidos:
    raise HTTPException(status_code=403, detail="Origen no permitido")


class StaticLocal(StaticFiles):
  """StaticFiles que también rechaza (403) a los clientes que no son locales."""

  async def __call__(self, scope, receive, send):
    if scope["type"] == "http" and not _es_local(scope):
      raise HTTPException(status_code=403, detail="El panel solo está disponible desde esta PC")
    await super().__call__(scope, receive, send)


router = APIRouter(dependencies=[Depends(solo_localhost)])
csrf = [Depends(verificar_origen)]


def instalar(app: FastAPI) -> None:
  """Agrega el panel. Llamar ANTES de incluir iclock.router (su comodín captura todo)."""
  app.include_router(router)
  app.mount("/static", StaticLocal(directory=BASE_DIR / "static"), name="static")


def _fecha(valor: str | None) -> str | None:
  """Normaliza a YYYY-MM-DD; None si falta o es inválida."""
  try:
    return date.fromisoformat(valor).isoformat() if valor else None
  except ValueError:
    return None


def _filtros(request: Request) -> tuple[str | None, str | None, str | None]:
  """(desde, hasta, pin) de la URL; los usan la tabla y el Excel."""
  q = request.query_params
  if "desde" not in q and "hasta" not in q:  # sin filtros de fecha: el día de hoy
    desde = hasta = date.today().isoformat()
  else:
    desde, hasta = _fecha(q.get("desde")), _fecha(q.get("hasta"))
  return desde, hasta, q.get("pin") or None


def _filas_marcaciones(filas, truncado: bool) -> list[dict]:
  """Filas para la tabla: fecha y hora separadas y el Tipo (misma regla que el Excel).

  Si la lista se cortó por el límite, el día más viejo puede estar incompleto y su Tipo
  sería engañoso (la "entrada" real quedó afuera): ese día se muestra sin Tipo.
  """
  tipos = jornada.tipos_de_marcaciones(filas)
  incompleto = min((f["fecha_hora"][:10] for f in filas), default=None) if truncado else None
  resultado = []
  for f, tipo in zip(filas, tipos):
    momento = datetime.fromisoformat(f["fecha_hora"])
    resultado.append({
      "fecha": f"{momento:%d/%m/%Y}", "hora": f"{momento:%H:%M:%S}", "pin": f["pin"],
      "nombre": f["nombre"], "verificacion": f["verificacion"], "sn": f["sn"],
      "tipo": "" if f["fecha_hora"][:10] == incompleto else tipo,
    })
  return resultado


def _contexto_marcaciones(request: Request) -> dict:
  desde, hasta, pin = _filtros(request)
  filas, truncado = db.listar_marcaciones(desde, hasta, pin, LIMITE_FILAS)
  return {
    "filas": _filas_marcaciones(filas, truncado),
    "truncado": truncado,
    "limite": LIMITE_FILAS,
    # La URL del refresco repite los filtros tal cual llegaron (sin filtros = siempre "hoy")
    "refresco": "/marcaciones/tabla?" + urlencode(list(request.query_params.items())),
    "ahora": datetime.now().strftime("%H:%M:%S"),
    "desde": desde or "",
    "hasta": hasta or "",
    "pin": pin or "",
  }


@router.get("/favicon.ico")
def favicon():
  """El navegador lo pide solo; se responde acá para que no caiga en el espía (samples)."""
  return Response(status_code=204)


@router.get("/")
def inicio():
  return RedirectResponse("/hoy")


def _contexto_hoy() -> dict:
  ahora = db.ahora()
  dia = ahora.date().isoformat()
  marcaciones, _ = db.listar_marcaciones(dia, dia, None, LIMITE_HOY)
  vista = jornada.vista_hoy(db.listar_empleados(), marcaciones, ahora)
  return {
    "vista": vista,
    "fecha_larga": jornada.fecha_larga(ahora),
    "dia_iso": dia,
    "hora": f"{ahora:%H:%M}",
    "actualizado": f"{ahora:%H:%M:%S}",
    "nadie_marco": bool(vista.filas) and vista.conteos[jornada.SIN_MARCAR] == len(vista.filas),
  }


@router.get("/hoy")
def hoy(request: Request, estado: str = "", q: str = ""):
  contexto = _contexto_hoy()
  # El filtro vive en la URL (lo aplica panel.js en el navegador); acá solo se repone en la página
  contexto.update(activo="hoy", estado=estado if estado in jornada.ESTADOS else "", q=q[:80])
  return templates.TemplateResponse(request, "hoy.html", contexto)


@router.get("/hoy/tabla")
def hoy_tabla(request: Request):
  """Parcial HTMX: planilla (principal) + título y resumen (fuera de banda), cada 5 s."""
  contexto = _contexto_hoy()
  contexto["oob"] = True
  return templates.TemplateResponse(request, "_hoy.html", contexto)


@router.get("/reloj")
def reloj_parcial(request: Request):
  """Parcial HTMX: indicador del reloj de la barra superior."""
  return templates.TemplateResponse(request, "_reloj.html", {})


@router.get("/marcaciones")
def marcaciones(request: Request):
  contexto = _contexto_marcaciones(request)
  contexto.update(activo="marcaciones", pins=db.listar_pins())
  return templates.TemplateResponse(request, "marcaciones.html", contexto)


@router.get("/marcaciones/tabla")
def marcaciones_tabla(request: Request):
  """Parcial HTMX: solo la tabla (se refresca sola cada pocos segundos)."""
  return templates.TemplateResponse(request, "_tabla_marcaciones.html",
                                    _contexto_marcaciones(request))


@router.get("/marcaciones/excel")
def marcaciones_excel(request: Request):
  """Descarga .xlsx con los mismos filtros que /marcaciones, sin el límite de filas de la tabla."""
  desde, hasta, pin = _filtros(request)
  filas, truncado = db.listar_marcaciones(desde, hasta, pin, reports.LIMITE_EXCEL)
  emp = db.obtener_empleado(pin) if pin else None
  contenido = reports.generar_excel(
    reversed(filas), desde, hasta, pin, emp["nombre"] if emp else None, truncado,
    colegio=colegio.leer()["nombre"], logo=colegio.ruta_logo(), tipo_logo=colegio.tipo_logo())
  nombre = f"asistencia_{desde or 'todo'}_{hasta or 'todo'}.xlsx"
  return Response(contenido, media_type=XLSX,
                  headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


def error_pin(pin: str) -> str | None:
  if not _PIN_RE.fullmatch(pin):
    return ("El PIN debe ser un número de 1 a 9 dígitos, sin ceros a la izquierda "
            "(por ejemplo 7, no 007).")
  return None


def error_nombre(nombre: str) -> str | None:
  """`nombre` ya viene sin espacios en los extremos."""
  if not nombre:
    return "El nombre es obligatorio."
  if len(nombre) > NOMBRE_MAX:
    return f"El nombre puede tener hasta {NOMBRE_MAX} caracteres (tiene {len(nombre)})."
  if any(ord(c) < 32 or ord(c) == 127 for c in nombre):
    return "El nombre no puede tener tabulaciones, saltos de línea ni otros caracteres de control."
  return None


def _privilegio(valor: str) -> int | None:
  try:
    privilegio = int(valor)
  except ValueError:
    return None
  return privilegio if privilegio in PRIVILEGIOS else None


def _contexto_estado() -> dict:
  """Lo que se refresca solo en /empleados: tabla de empleados y últimos comandos."""
  return {
    "empleados": db.listar_empleados(),
    "comandos": db.listar_comandos(LIMITE_COMANDOS),
    "ahora": datetime.now().strftime("%H:%M:%S"),
  }


def _pagina_empleados(request: Request, error: str | None = None, status_code: int = 200,
                      form: dict | None = None):
  contexto = _contexto_estado()
  contexto.update(
    activo="empleados", error=error,
    form=form or {"pin": "", "nombre": "", "privilegio": "0"},
  )
  return templates.TemplateResponse(request, "empleados.html", contexto, status_code=status_code)


def _pagina_editar(request: Request, emp, error: str | None = None, status_code: int = 200,
                   form: dict | None = None):
  form = form or {"nombre": emp["nombre"], "privilegio": str(emp["privilegio"] or 0)}
  return templates.TemplateResponse(
    request, "empleado_editar.html",
    {"activo": "empleados", "emp": emp, "error": error, "form": form}, status_code=status_code,
  )


def _error_gestion(emp) -> tuple[int, str] | None:
  """Por qué no se puede modificar / dar de baja a `emp` desde el panel (None si se puede)."""
  if emp is None:
    return 404, "No existe ese empleado."
  if emp["privilegio"] == ADMIN:
    return 403, ("Los administradores no se modifican ni se dan de baja desde el panel: "
                 "se gestionan en el propio reloj (un cambio desde acá podría borrarles la "
                 "contraseña o dejar el reloj sin administrador).")
  if emp["baja_pendiente"]:
    return 409, "Ese empleado ya tiene una baja pendiente."
  return None


@router.get("/empleados")
def empleados(request: Request):
  return _pagina_empleados(request)


@router.get("/empleados/estado")
def empleados_estado(request: Request):
  """Parcial HTMX: tabla de empleados + (fuera de banda) últimos comandos."""
  contexto = _contexto_estado()
  contexto["oob"] = True
  return templates.TemplateResponse(request, "_estado_empleados.html", contexto)


@router.post("/empleados", dependencies=csrf)
def empleado_alta(request: Request, pin: str = Form(""), nombre: str = Form(""),
                  privilegio: str = Form("0")):
  pin, nombre = pin.strip(), nombre.strip()
  form = {"pin": pin, "nombre": nombre, "privilegio": privilegio}
  pri = _privilegio(privilegio)
  error = error_pin(pin) or error_nombre(nombre)
  if not error and pri is None:
    error = "El privilegio tiene que ser Usuario o Administrador."
  if error:
    return _pagina_empleados(request, error, 400, form)
  if db.obtener_empleado(pin):
    return _pagina_empleados(
      request, f"Ya existe un empleado con PIN {pin} (para cambiarlo usá Editar).", 409, form)
  reloj = db.ultimo_reloj()
  if reloj is None:
    return _pagina_empleados(
      request, "Todavía no se conectó ningún reloj: no hay a dónde enviar el comando.", 409, form)
  try:
    db.guardar_empleado_y_encolar("alta", reloj["sn"], pin, nombre, pri,
                                  comando_usuario(pin, nombre, pri))
  except ValueError:  # alguien lo creó entre el chequeo y el guardado
    return _pagina_empleados(
      request, f"Ya existe un empleado con PIN {pin} (para cambiarlo usá Editar).", 409, form)
  return RedirectResponse("/empleados", status_code=303)


@router.get("/empleados/{pin}/editar")
def empleado_editar(request: Request, pin: str):
  emp = db.obtener_empleado(pin)
  if (rechazo := _error_gestion(emp)):
    return _pagina_empleados(request, rechazo[1], rechazo[0])
  return _pagina_editar(request, emp)


@router.post("/empleados/{pin}/editar", dependencies=csrf)
def empleado_modificar(request: Request, pin: str, nombre: str = Form(""),
                       privilegio: str = Form("0")):
  emp = db.obtener_empleado(pin)
  if (rechazo := _error_gestion(emp)):
    return _pagina_empleados(request, rechazo[1], rechazo[0])
  nombre = nombre.strip()
  form = {"nombre": nombre, "privilegio": privilegio}
  pri = _privilegio(privilegio)
  error = error_nombre(nombre)
  if not error and pri is None:
    error = "El privilegio tiene que ser Usuario o Administrador."
  if error:
    return _pagina_editar(request, emp, error, 400, form)
  texto = comando_usuario(pin, nombre, pri, emp["tarjeta"] or "",
                          1 if emp["grupo"] is None else emp["grupo"])
  db.guardar_empleado_y_encolar("modificacion", emp["sn"], pin, nombre, pri, texto)
  return RedirectResponse("/empleados", status_code=303)


@router.post("/empleados/{pin}/baja", dependencies=csrf)
def empleado_baja(request: Request, pin: str):
  emp = db.obtener_empleado(pin)
  if (rechazo := _error_gestion(emp)):
    return _pagina_empleados(request, rechazo[1], rechazo[0])
  db.encolar_comando(emp["sn"], pin, "baja", comando_baja(pin))  # la fila se borra al confirmar
  return RedirectResponse("/empleados", status_code=303)


# --- Configuración: nombre y logo del colegio -------------------------------------------------

def _pagina_configuracion(request: Request, error: str | None = None, status_code: int = 200,
                          nombre: str | None = None):
  return templates.TemplateResponse(
    request, "configuracion.html",
    {"activo": "configuracion", "error": error, "guardado": "guardado" in request.query_params,
     "nombre": colegio.leer()["nombre"] if nombre is None else nombre,
     "logo_tipo": colegio.tipo_logo(), "nombre_max": colegio.NOMBRE_MAX,
     "logo_max_kb": colegio.LOGO_MAX_BYTES // 1024},
    status_code=status_code,
  )


@router.get("/configuracion")
def configuracion(request: Request):
  return _pagina_configuracion(request)


@router.post("/configuracion", dependencies=csrf)
def configuracion_guardar(request: Request, nombre: str = Form(""),
                          logo: UploadFile | None = File(None)):
  """Guarda nombre y (si viene) logo. Si algo no es válido no se guarda nada."""
  nombre = nombre.strip()
  error = colegio.error_nombre(nombre)
  nuevo_logo = None
  if not error and logo is not None and logo.filename:
    contenido = logo.file.read(colegio.LOGO_MAX_BYTES + 1)
    ext, error = colegio.validar_logo(contenido)
    if ext:
      nuevo_logo = (ext, contenido)
  if error:
    return _pagina_configuracion(request, error, 400, nombre)
  colegio.guardar(nombre, nuevo_logo)
  return RedirectResponse("/configuracion?guardado=1", status_code=303)


@router.post("/configuracion/logo/quitar", dependencies=csrf)
def configuracion_quitar_logo():
  colegio.quitar_logo()
  return RedirectResponse("/configuracion?guardado=1", status_code=303)


@router.get("/colegio/logo")
def colegio_logo():
  """El logo cargado en Configuración (solo desde esta PC, como todo el panel)."""
  ruta = colegio.ruta_logo()
  if ruta is None:
    raise HTTPException(status_code=404, detail="Todavía no se cargó un logo")
  # Un SVG abierto directo no puede ejecutar nada: sin scripts y en sandbox
  return FileResponse(ruta, media_type=colegio.tipo_logo(), headers={
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-cache",
  })
