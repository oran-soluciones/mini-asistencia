"""Base SQLite: esquema y consultas (sqlite3 estándar, sin ORM)."""
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from app.config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS marcaciones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sn TEXT NOT NULL,
  pin TEXT NOT NULL,
  fecha_hora TEXT NOT NULL,  -- YYYY-MM-DD HH:MM:SS, hora local del reloj
  estado INTEGER,
  verificacion INTEGER,
  raw TEXT NOT NULL,         -- línea original del reloj
  recibido TEXT NOT NULL,    -- timestamp de la PC al recibirla
  UNIQUE (sn, pin, fecha_hora)
)
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
  """Abre una conexión nueva (una por operación) y crea el esquema si falta.

  `path` permite apuntar a otra base (tests). Usar con `closing(connect())`.
  """
  conn = sqlite3.connect(path or DB_PATH, timeout=10)
  conn.row_factory = sqlite3.Row
  conn.execute(_SCHEMA)
  return conn


def insert_marcaciones(sn: str, marcaciones: list, path: Path | None = None) -> int:
  """Guarda las marcaciones; las repetidas (sn, pin, fecha_hora) se ignoran.

  Devuelve cuántas eran nuevas. Si algo falla no se guarda ninguna (transacción).
  """
  recibido = datetime.now().isoformat(sep=" ", timespec="seconds")
  filas = [(sn, m.pin, m.fecha_hora, m.estado, m.verificacion, m.raw, recibido)
           for m in marcaciones]
  with closing(connect(path)) as conn, conn:
    antes = conn.total_changes
    conn.executemany(
      "INSERT OR IGNORE INTO marcaciones (sn, pin, fecha_hora, estado, verificacion, raw, recibido)"
      " VALUES (?, ?, ?, ?, ?, ?, ?)",
      filas,
    )
    return conn.total_changes - antes
