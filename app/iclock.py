"""Servidor del protocolo ADMS/PUSH (rutas /iclock/*).

Loguea y guarda en samples/ cada request crudo que manda el reloj y responde lo mínimo
para que siga hablando. Las marcaciones (ATTLOG) y los empleados (líneas USER de OPERLOG)
además se guardan en SQLite.
"""
import logging
import sqlite3
from datetime import datetime
from typing import NamedTuple

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app import db
from app.config import SAMPLES_DIR

log = logging.getLogger("iclock")
router = APIRouter()


class Marcacion(NamedTuple):
  pin: str
  fecha_hora: str  # YYYY-MM-DD HH:MM:SS, hora local del reloj
  estado: int | None
  verificacion: int | None  # 15 = cara (deducido, no verificado)
  raw: str


def _to_int(value: str) -> int | None:
  try:
    return int(value)
  except ValueError:
    return None


def parse_attlog(body: str) -> list[Marcacion]:
  """Parsea el body de ATTLOG: una marcación por línea, campos separados por tab.

  Formato: PIN, YYYY-MM-DD HH:MM:SS, estado, verificación, ceros (tab final).
  Ignora líneas vacías; salta (con warning) las mal formadas sin romper el resto.
  """
  marcaciones = []
  for line in body.splitlines():
    if not line.strip():
      continue
    campos = line.split("\t")
    pin = campos[0].strip()
    try:
      if len(campos) < 2 or not pin:
        raise ValueError("faltan campos o PIN vacío")
      fecha_hora = datetime.strptime(campos[1].strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
      log.warning("ATTLOG línea mal formada (%s), se salta: %r", e, line)
      continue
    marcaciones.append(Marcacion(
      pin=pin,
      fecha_hora=f"{fecha_hora:%Y-%m-%d %H:%M:%S}",
      estado=_to_int(campos[2].strip()) if len(campos) > 2 else None,
      verificacion=_to_int(campos[3].strip()) if len(campos) > 3 else None,
      raw=line,
    ))
  return marcaciones


class Usuario(NamedTuple):
  pin: str
  nombre: str
  privilegio: int | None
  tarjeta: str
  grupo: int | None
  # Passwd viene en la línea USER pero a propósito NO se guarda en ningún lado


def parse_users(body: str) -> list[Usuario]:
  """Parsea las líneas `USER` del body de OPERLOG (campos `clave=valor` separados por tab).

  Ignora el resto de las líneas (OPLOG, vacías). Salta con warning las USER sin PIN.
  Nunca loguea la línea porque trae la contraseña (Passwd), que se descarta.
  """
  usuarios = []
  for n, line in enumerate(body.splitlines(), start=1):
    if not line.startswith("USER "):
      continue
    campos = {}
    for campo in line[len("USER "):].split("\t"):
      clave, sep, valor = campo.partition("=")
      if sep:
        campos[clave.strip()] = valor.strip()
    pin = campos.get("PIN", "")
    if not pin:
      log.warning("OPERLOG línea %d: USER sin PIN, se salta", n)
      continue
    usuarios.append(Usuario(
      pin=pin,
      nombre=campos.get("Name", ""),
      privilegio=_to_int(campos.get("Pri", "")),
      tarjeta=campos.get("Card", ""),
      grupo=_to_int(campos.get("Grp", "")),
    ))
  return usuarios


def _options_response(sn: str) -> str:
  # Formato del protocolo PUSH clásico (no verificado). ATTLOGStamp=None pide todas las
  # marcaciones guardadas, útil para capturar samples. Sin TimeZone para no tocar la hora.
  return "\n".join([
    f"GET OPTION FROM: {sn}",
    "ATTLOGStamp=None",
    "OPERLOGStamp=None",
    "ATTPHOTOStamp=None",
    "ErrorDelay=30",
    "Delay=10",
    "TransTimes=00:00;14:05",
    "TransInterval=1",
    "TransFlag=TransData AttLog OpLog EnrollUser ChgUser UserPic",
    "Realtime=1",
    "Encrypt=None",
  ]) + "\n"


def _reply(request: Request) -> str:
  path = request.url.path.lower()
  if request.method == "GET" and path.endswith("/cdata") and "options" in request.query_params:
    return _options_response(request.query_params.get("SN", ""))
  return "OK"


def _save_sample(request: Request, body: bytes, reply: str) -> None:
  now = datetime.now()
  name = request.url.path.strip("/").replace("/", "_") or "root"
  fname = f"{now:%Y%m%d-%H%M%S-%f}_{request.method}_{name}.txt"
  client = request.client.host if request.client else "?"
  query = "?" + request.url.query if request.url.query else ""
  head = [
    f"# capturado {now.isoformat()} desde {client}",
    f"{request.method} {request.url.path}{query}",
  ]
  head += [f"{k}: {v}" for k, v in request.headers.items()]
  tail = f"\n\n# ---- respuesta enviada ----\n{reply}"
  # El body se guarda tal cual (bytes) para no perder nada
  (SAMPLES_DIR / fname).write_bytes(
    ("\n".join(head) + "\n\n").encode("utf-8") + body + tail.encode("utf-8")
  )


def _guardar(table: str | None, sn: str, text: str) -> None:
  """Guarda en SQLite lo que traiga el POST a cdata. Levanta sqlite3.Error si falla."""
  if table == "ATTLOG":
    marcaciones = parse_attlog(text)
    nuevas = db.insert_marcaciones(sn, marcaciones)
    log.info("ATTLOG SN=%s recibidas=%d nuevas=%d", sn, len(marcaciones), nuevas)
  elif table == "OPERLOG":  # las líneas OPLOG se ignoran por ahora
    usuarios = parse_users(text)
    if usuarios:
      db.upsert_empleados(sn, usuarios)
      log.info("OPERLOG SN=%s empleados=%d", sn, len(usuarios))


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
async def spy(request: Request, path: str):
  """Comodín: captura /iclock/* y cualquier otra ruta que use el firmware."""
  body = await request.body()
  reply = _reply(request)
  log.info(
    "%s %s query=%s headers=%s body=%r -> %r",
    request.method, request.url.path, dict(request.query_params),
    dict(request.headers), body, reply,
  )
  _save_sample(request, body, reply)
  if request.method == "POST" and request.url.path.lower() == "/iclock/cdata":
    table = request.query_params.get("table")
    sn = request.query_params.get("SN", "")
    try:
      _guardar(table, sn, body.decode("utf-8", errors="replace"))
    except sqlite3.Error:
      # No responder OK si no se guardó: así el reloj reintenta y no se pierden datos
      # (que reintente ante un 500 no está verificado). El request crudo ya está en samples/.
      log.exception("%s SN=%s: no se pudo guardar en la base", table, sn)
      return PlainTextResponse("ERROR", status_code=500)
  return PlainTextResponse(reply)
