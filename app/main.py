"""Punto de entrada: servidor /iclock (reloj) + panel web local + ícono en la bandeja.

Uso: .venv\\Scripts\\python.exe -m app.main [--sin-navegador] [--sin-bandeja]
En el .exe (PyInstaller) es lo que corre el doble clic:
- Si el programa ya está abierto, solo abre el panel en el navegador y termina.
- Si el puerto lo usa otro programa (p. ej. ZKBio Time), avisa y termina.
- Levanta el servidor en un hilo, abre el navegador y deja el ícono en la bandeja
  (Abrir panel, Iniciar con Windows, Carpeta de datos, Salir).
- --sin-navegador: arranque con Windows, sin abrir el navegador.
"""
import logging
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from logging.handlers import RotatingFileHandler

import uvicorn
from fastapi import FastAPI

from app import iclock, panel
from app.config import DATA_DIR, EMPAQUETADO, HOST, LOG_DIR, PORT, SAMPLES_DIR

_handlers: list[logging.Handler] = [
  # Rotativo: el log crudo de cada request no puede crecer sin límite (10 x 5 MB)
  RotatingFileHandler(LOG_DIR / "iclock.log", maxBytes=5_000_000, backupCount=10,
                      encoding="utf-8"),
]
if sys.stderr:  # en el .exe sin consola no hay stderr
  _handlers.append(logging.StreamHandler())
logging.basicConfig(level=logging.INFO, handlers=_handlers,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("iclock")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
panel.instalar(app)  # antes que iclock: su comodín /{path:path} captura todo lo demás
app.include_router(iclock.router)

URL = f"http://localhost:{PORT}/"
NOMBRE = "mini-asistencia"
ICONO = panel.BASE_DIR / "static" / "icono.ico"  # en el .exe main.py no queda dentro de app/
CLAVE_INICIO = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _puerto_ocupado() -> bool:
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(1)
    return s.connect_ex(("127.0.0.1", PORT)) == 0


def _es_nuestro() -> bool:
  """True si en el puerto ya corre mini-asistencia (responde el panel)."""
  try:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/hoy", timeout=3) as r:
      return b"mini-asistencia" in r.read(4096)
  except OSError:
    return False


def _aviso(texto: str) -> None:
  """Cartel de Windows (en el .exe no hay consola donde mostrar el error)."""
  log.error(texto)
  if os.name == "nt":
    import ctypes
    ctypes.windll.user32.MessageBoxW(None, texto, NOMBRE, 0x10)  # ícono de error


def _abrir_panel(*_args) -> None:
  webbrowser.open(URL)


# --- Iniciar con Windows (registro del usuario, solo en el .exe) ----------------------------

def _comando_inicio() -> str:
  return f'"{sys.executable}" --sin-navegador'


def inicio_con_windows() -> bool:
  if os.name != "nt" or not EMPAQUETADO:
    return False
  import winreg
  try:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_INICIO) as clave:
      return winreg.QueryValueEx(clave, NOMBRE)[0] == _comando_inicio()
  except OSError:
    return False


def cambiar_inicio_con_windows(*_args) -> None:
  import winreg
  activo = inicio_con_windows()
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_INICIO, 0, winreg.KEY_SET_VALUE) as clave:
    if activo:
      winreg.DeleteValue(clave, NOMBRE)
    else:
      winreg.SetValueEx(clave, NOMBRE, 0, winreg.REG_SZ, _comando_inicio())
  log.info("Iniciar con Windows: %s", "desactivado" if activo else "activado")


def _abrir_carpeta_datos(*_args) -> None:
  if os.name == "nt":
    os.startfile(DATA_DIR)


# --- Arranque ---------------------------------------------------------------------------------

def _bandeja(servidor: uvicorn.Server) -> None:
  """Ícono en la bandeja; bloquea hasta que se elige Salir."""
  import pystray
  from PIL import Image

  def salir(icono, _item):
    log.info("Salir desde la bandeja")
    servidor.should_exit = True
    icono.stop()

  opciones = [
    pystray.MenuItem("Abrir panel", _abrir_panel, default=True),
  ]
  if EMPAQUETADO and os.name == "nt":
    opciones.append(pystray.MenuItem("Iniciar con Windows", cambiar_inicio_con_windows,
                                     checked=lambda _item: inicio_con_windows()))
  opciones += [
    pystray.MenuItem("Carpeta de datos", _abrir_carpeta_datos),
    pystray.Menu.SEPARATOR,
    pystray.MenuItem("Salir", salir),
  ]
  icono = pystray.Icon(NOMBRE, Image.open(ICONO), f"{NOMBRE} (puerto {PORT})",
                       pystray.Menu(*opciones))
  icono.run()


def main() -> None:
  args = sys.argv[1:]
  if _puerto_ocupado():
    if _es_nuestro():  # doble clic con el programa ya abierto: solo mostrar el panel
      if "--sin-navegador" not in args:
        _abrir_panel()
      return
    _aviso(f"El puerto {PORT} lo está usando otro programa (¿ZKBio Time?).\n\n"
           "Cerralo y volvé a abrir mini-asistencia: el reloj manda las marcaciones a ese puerto.")
    sys.exit(1)

  log.info("Escuchando en %s:%s | datos: %s | samples: %s", HOST, PORT, DATA_DIR, SAMPLES_DIR)
  log.info("Panel (solo desde esta PC): %s", URL)
  servidor = uvicorn.Server(uvicorn.Config(app, host=HOST, port=PORT, log_config=None))
  hilo = threading.Thread(target=servidor.run, name="servidor", daemon=True)
  hilo.start()
  for _ in range(100):  # hasta 10 s
    if servidor.started or not hilo.is_alive():
      break
    time.sleep(0.1)
  if not servidor.started:
    _aviso(f"No se pudo iniciar el servidor en el puerto {PORT}. Detalle en {LOG_DIR}.")
    sys.exit(1)
  if "--sin-navegador" not in args:
    _abrir_panel()

  if "--sin-bandeja" in args:
    hilo.join()
    return
  try:
    _bandeja(servidor)
  except Exception:  # sin bandeja disponible: el servidor sigue igual
    log.exception("No se pudo crear el ícono de la bandeja; el servidor sigue andando")
    hilo.join()
    return
  hilo.join(timeout=5)


if __name__ == "__main__":
  main()
