"""Panel web: marcaciones y empleados (con ABM). Jinja2 + HTMX.

Solo responde a clientes locales (127.0.0.1 / ::1): el servidor escucha en toda la red
porque el reloj lo necesita, pero el panel no tiene que verse desde afuera. Los POST además
rechazan orígenes ajenos (CSRF: una web abierta en el navegador podría postear a localhost).
"""
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import db
from app.config import PORT
from app.iclock import comando_baja, comando_usuario

BASE_DIR = Path(__file__).resolve().parent
LIMITE_FILAS = 500
LIMITE_COMANDOS = 20
RELOJ_CONECTADO_SEGUNDOS = 30  # último contacto más reciente que esto = reloj conectado
ADMIN = 14  # privilegio de administrador (deducido del único usuario real, no verificado)
PRIVILEGIOS = {0: "Usuario", ADMIN: "Administrador"}
NOMBRE_MAX = 24
_LOCALES = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
_PIN_RE = re.compile(r"[1-9][0-9]{0,8}")


def etiqueta_estado(estado: str, codigo: int | None) -> str:
  if estado == "ok":
    return "confirmado"
  if estado == "error":
    return f"error (código {codigo})" if codigo is not None else "error (sin respuesta)"
  return estado


templates = Jinja2Templates(directory=BASE_DIR / "templates")  # autoescape activado
templates.env.globals.update(etiqueta_estado=etiqueta_estado, PRIVILEGIOS=PRIVILEGIOS, ADMIN=ADMIN)


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


def _contexto_marcaciones(request: Request) -> dict:
  q = request.query_params
  if "desde" not in q and "hasta" not in q:  # sin filtros de fecha: el día de hoy
    desde = hasta = date.today().isoformat()
  else:
    desde, hasta = _fecha(q.get("desde")), _fecha(q.get("hasta"))
  pin = q.get("pin") or None
  filas, truncado = db.listar_marcaciones(desde, hasta, pin, LIMITE_FILAS)
  return {
    "filas": filas,
    "truncado": truncado,
    "limite": LIMITE_FILAS,
    # La URL del refresco repite los filtros tal cual llegaron (sin filtros = siempre "hoy")
    "refresco": "/marcaciones/tabla?" + urlencode(list(q.items())),
    "ahora": datetime.now().strftime("%H:%M:%S"),
    "desde": desde or "",
    "hasta": hasta or "",
    "pin": pin or "",
  }


@router.get("/")
def inicio():
  return RedirectResponse("/marcaciones")


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


def _hace_txt(segundos: int) -> str:
  if segundos < 120:
    return f"{segundos} s"
  if segundos < 7200:
    return f"{segundos // 60} min"
  return f"{segundos // 3600} h"


def _contexto_estado() -> dict:
  """Lo que se refresca solo en /empleados: reloj, tabla de empleados y últimos comandos."""
  reloj = db.ultimo_reloj()
  hace = None
  if reloj:
    ultimo = datetime.fromisoformat(reloj["ultimo_contacto"])
    hace = max(0, int((db.ahora() - ultimo).total_seconds()))
  return {
    "empleados": db.listar_empleados(),
    "comandos": db.listar_comandos(LIMITE_COMANDOS),
    "reloj": reloj,
    "hace": None if hace is None else _hace_txt(hace),
    "conectado": hace is not None and hace < RELOJ_CONECTADO_SEGUNDOS,
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
  """Parcial HTMX: tabla de empleados + (fuera de banda) reloj y últimos comandos."""
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
