"""Etapa 1 - servidor espía del protocolo ADMS/PUSH.

Loguea y guarda en samples/ cada request crudo que manda el reloj y responde lo mínimo
para que siga hablando. Las respuestas NO están verificadas contra este firmware: los
samples capturados dirán si las acepta.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.config import SAMPLES_DIR

log = logging.getLogger("iclock")
router = APIRouter()


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
    head = [f"# capturado {now.isoformat()} desde {request.client.host if request.client else '?'}",
            f"{request.method} {request.url.path}{'?' + request.url.query if request.url.query else ''}"]
    head += [f"{k}: {v}" for k, v in request.headers.items()]
    tail = f"\n\n# ---- respuesta enviada ----\n{reply}"
    # El body se guarda tal cual (bytes) para no perder nada
    (SAMPLES_DIR / fname).write_bytes(
        ("\n".join(head) + "\n\n").encode("utf-8") + body + tail.encode("utf-8"))


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
async def spy(request: Request, path: str):
    """Comodín: captura /iclock/* y cualquier otra ruta que use el firmware."""
    body = await request.body()
    reply = _reply(request)
    log.info("%s %s query=%s headers=%s body=%r -> %r", request.method, request.url.path,
             dict(request.query_params), dict(request.headers), body, reply)
    _save_sample(request, body, reply)
    return PlainTextResponse(reply)
