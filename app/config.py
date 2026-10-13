"""Configuración: puerto y rutas (siempre con pathlib)."""
import os
from pathlib import Path

HOST = "0.0.0.0"  # /iclock tiene que ser accesible desde el reloj por la red
PORT = int(os.environ.get("MINI_ASISTENCIA_PORT", "8081"))

# Carpeta de datos del usuario (SQLite, logs): nunca al lado del .exe
if os.name == "nt":
  DATA_DIR = Path(os.environ["LOCALAPPDATA"]) / "mini-asistencia"
else:
  DATA_DIR = Path.home() / ".local" / "share" / "mini-asistencia"
LOG_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "asistencia.db"

# Requests reales capturados del reloj (local, fuera de Git; los tests usan tests/fixtures/)
SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

for _d in (DATA_DIR, LOG_DIR, SAMPLES_DIR):
  _d.mkdir(parents=True, exist_ok=True)
