"""Punto de entrada. Etapa 1: solo el servidor espía (sin panel ni bandeja todavía).

Uso: .venv\\Scripts\\python.exe -m app.main
"""
import logging

import uvicorn
from fastapi import FastAPI

from app import iclock
from app.config import HOST, LOG_DIR, PORT, SAMPLES_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler(LOG_DIR / "iclock.log", encoding="utf-8")],
)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(iclock.router)


def main() -> None:
    logging.getLogger("iclock").info(
        "Escuchando en %s:%s | samples: %s | log: %s", HOST, PORT, SAMPLES_DIR, LOG_DIR)
    uvicorn.run(app, host=HOST, port=PORT, log_config=None)


if __name__ == "__main__":
    main()
