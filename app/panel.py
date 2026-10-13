"""Panel web (solo lectura): marcaciones y empleados. Jinja2 + HTMX.

Solo responde a clientes locales (127.0.0.1 / ::1): el servidor escucha en toda la red
porque el reloj lo necesita, pero el panel no tiene que verse desde afuera.
"""
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import db

BASE_DIR = Path(__file__).resolve().parent
LIMITE_FILAS = 500
_LOCALES = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}

templates = Jinja2Templates(directory=BASE_DIR / "templates")  # autoescape activado


def _es_local(scope) -> bool:
  client = scope.get("client")
  return bool(client) and client[0] in _LOCALES


def solo_localhost(request: Request) -> None:
  if not _es_local(request.scope):
    raise HTTPException(status_code=403, detail="El panel solo está disponible desde esta PC")


class StaticLocal(StaticFiles):
  """StaticFiles que también rechaza (403) a los clientes que no son locales."""

  async def __call__(self, scope, receive, send):
    if scope["type"] == "http" and not _es_local(scope):
      raise HTTPException(status_code=403, detail="El panel solo está disponible desde esta PC")
    await super().__call__(scope, receive, send)


router = APIRouter(dependencies=[Depends(solo_localhost)])


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


@router.get("/empleados")
def empleados(request: Request):
  return templates.TemplateResponse(
    request, "empleados.html", {"activo": "empleados", "empleados": db.listar_empleados()}
  )
