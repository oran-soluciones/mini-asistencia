"""Punto de entrada: servidor /iclock (reloj) + panel web local (sin bandeja todavía).

Uso: .venv\\Scripts\\python.exe -m app.main
"""
import logging

import uvicorn
from fastapi import FastAPI

from app import iclock, panel
from app.config import HOST, LOG_DIR, PORT, SAMPLES_DIR

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s %(levelname)s %(name)s: %(message)s",
  handlers=[
    logging.StreamHandler(),
    logging.FileHandler(LOG_DIR / "iclock.log", encoding="utf-8"),
  ],
)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
panel.instalar(app)  # antes que iclock: su comodín /{path:path} captura todo lo demás
app.include_router(iclock.router)


def main() -> None:
  log = logging.getLogger("iclock")
  log.info("Escuchando en %s:%s | samples: %s | log: %s", HOST, PORT, SAMPLES_DIR, LOG_DIR)
  log.info("Panel (solo desde esta PC): http://localhost:%s/", PORT)
  uvicorn.run(app, host=HOST, port=PORT, log_config=None)


if __name__ == "__main__":
  main()
