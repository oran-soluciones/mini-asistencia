"""Configuración: puerto y rutas (siempre con pathlib)."""
import os
import sys
from pathlib import Path

# True dentro del .exe de PyInstaller (los archivos del programa están en una carpeta temporal)
EMPAQUETADO = getattr(sys, "frozen", False)

HOST = "0.0.0.0"  # /iclock tiene que ser accesible desde el reloj por la red
PORT = int(os.environ.get("MINI_ASISTENCIA_PORT", "8081"))

# Carpeta de datos del usuario (SQLite, logs): nunca al lado del .exe.
# MINI_ASISTENCIA_DATA_DIR permite apuntar a otra carpeta (pruebas manuales).
if "MINI_ASISTENCIA_DATA_DIR" in os.environ:
  DATA_DIR = Path(os.environ["MINI_ASISTENCIA_DATA_DIR"])
elif os.name == "nt":
  DATA_DIR = Path(os.environ["LOCALAPPDATA"]) / "mini-asistencia"
else:
  DATA_DIR = Path.home() / ".local" / "share" / "mini-asistencia"
LOG_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "asistencia.db"

# Requests reales capturados del reloj (local, fuera de Git; los tests usan tests/fixtures/).
# En el .exe van a la carpeta de datos: al lado del programa no se puede escribir.
if os.environ.get("MINI_ASISTENCIA_SAMPLES_DIR"):
  SAMPLES_DIR = Path(os.environ["MINI_ASISTENCIA_SAMPLES_DIR"])
elif EMPAQUETADO:
  SAMPLES_DIR = DATA_DIR / "samples"
else:
  SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

for _d in (DATA_DIR, LOG_DIR, SAMPLES_DIR):
  _d.mkdir(parents=True, exist_ok=True)
