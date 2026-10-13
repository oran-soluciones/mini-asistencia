"""Nombre y logo del colegio: se cargan desde el panel (Configuración), nunca en el código.

Se guardan en la carpeta de datos del usuario: `colegio.json` (nombre y archivo del logo) y
`logo.<ext>`. El tipo del logo se decide por su contenido, no por el nombre del archivo.
"""
import json
import logging
import re
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app import config

log = logging.getLogger("panel")

NOMBRE_MAX = 80
LOGO_MAX_BYTES = 1024 * 1024
LOGO_MAX_PIXELES = 25_000_000  # tope para no armar imágenes enormes en memoria
_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"
_SVG_RE = re.compile(r"<svg[\s>/]", re.IGNORECASE)
# Peligrosos en un SVG: scripts, manejadores onXXX= y URLs javascript:
_SVG_PELIGRO_RE = re.compile(r"<\s*script|\bon[a-z]+\s*=|javascript\s*:|<\s*foreignObject",
                             re.IGNORECASE)
EXTENSIONES = {"png": "image/png", "jpg": "image/jpeg", "svg": "image/svg+xml"}


def _archivo_config() -> Path:
  return config.DATA_DIR / "colegio.json"


def leer() -> dict:
  """{'nombre': str, 'logo': 'logo.png' | None}. Si falta o está dañado: vacío."""
  try:
    datos = json.loads(_archivo_config().read_text(encoding="utf-8"))
  except FileNotFoundError:
    datos = {}
  except (OSError, ValueError) as e:
    log.warning("No se pudo leer colegio.json (%s): se usa vacío", e)
    datos = {}
  nombre = datos.get("nombre") if isinstance(datos, dict) else ""
  logo = datos.get("logo") if isinstance(datos, dict) else None
  if not isinstance(logo, str) or logo.rpartition(".")[2] not in EXTENSIONES \
      or not (config.DATA_DIR / logo).is_file():
    logo = None
  return {"nombre": nombre if isinstance(nombre, str) else "", "logo": logo}


def ruta_logo() -> Path | None:
  logo = leer()["logo"]
  return config.DATA_DIR / logo if logo else None


def tipo_logo() -> str | None:
  """'image/png' | 'image/jpeg' | 'image/svg+xml' del logo guardado, o None si no hay."""
  logo = leer()["logo"]
  return EXTENSIONES[logo.rpartition(".")[2]] if logo else None


def version_logo() -> str:
  """Cambia cada vez que se reemplaza el logo (para que el navegador no use uno viejo)."""
  ruta = ruta_logo()
  return str(ruta.stat().st_mtime_ns) if ruta else ""


def error_nombre(nombre: str) -> str | None:
  """`nombre` ya viene sin espacios en los extremos. Vacío es válido (sin nombre cargado)."""
  if len(nombre) > NOMBRE_MAX:
    return f"El nombre puede tener hasta {NOMBRE_MAX} caracteres (tiene {len(nombre)})."
  if any(ord(c) < 32 or ord(c) == 127 for c in nombre):
    return "El nombre no puede tener tabulaciones, saltos de línea ni otros caracteres de control."
  return None


def validar_logo(contenido: bytes) -> tuple[str | None, str | None]:
  """(extensión, error): extensión 'png' | 'jpg' | 'svg' si el contenido es válido."""
  if not contenido:
    return None, "El archivo está vacío."
  if len(contenido) > LOGO_MAX_BYTES:
    return None, "El logo pesa más de 1 MB. Probá con una imagen más liviana."
  if contenido.startswith(_PNG):
    ext = "png"
  elif contenido.startswith(_JPEG):
    ext = "jpg"
  else:
    ext = None
  if ext:
    try:
      with Image.open(BytesIO(contenido)) as img:
        if img.width * img.height > LOGO_MAX_PIXELES:
          return None, "La imagen es demasiado grande en píxeles. Probá con una más chica."
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
      return None, "La imagen está dañada o no se puede leer."
    return ext, None
  try:
    texto = contenido.decode("utf-8-sig")
  except UnicodeDecodeError:
    return None, "El logo tiene que ser PNG, JPG o SVG."
  if not _SVG_RE.search(texto):
    return None, "El logo tiene que ser PNG, JPG o SVG."
  if _SVG_PELIGRO_RE.search(texto):
    return None, "El SVG tiene código activo (scripts, eventos o enlaces javascript:); no se acepta."
  return "svg", None


def _escribir(ruta: Path, contenido: bytes) -> None:
  """Escritura atómica: o queda el archivo viejo o el nuevo, nunca uno a medias."""
  temporal = ruta.with_name(ruta.name + ".tmp")
  temporal.write_bytes(contenido)
  temporal.replace(ruta)


def guardar(nombre: str, logo: tuple[str, bytes] | None = None) -> None:
  """Guarda el nombre y, si viene, el logo `(extensión, contenido)` ya validado."""
  actual = leer()
  archivo_logo = actual["logo"]
  if logo:
    ext, contenido = logo
    archivo_logo = f"logo.{ext}"
    _escribir(config.DATA_DIR / archivo_logo, contenido)
    _borrar_logos(salvo=archivo_logo)
  _escribir(_archivo_config(),
            json.dumps({"nombre": nombre, "logo": archivo_logo}, ensure_ascii=False).encode())


def _borrar_logos(salvo: str | None = None) -> None:
  for ext in EXTENSIONES:
    candidato = config.DATA_DIR / f"logo.{ext}"
    if candidato.name != salvo and candidato.is_file():
      candidato.unlink()


def quitar_logo() -> None:
  actual = leer()
  _borrar_logos()
  _escribir(_archivo_config(),
            json.dumps({"nombre": actual["nombre"], "logo": None}, ensure_ascii=False).encode())
