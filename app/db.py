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
);
CREATE INDEX IF NOT EXISTS idx_marcaciones_fecha ON marcaciones (fecha_hora);
CREATE TABLE IF NOT EXISTS empleados (
  pin TEXT PRIMARY KEY,
  nombre TEXT NOT NULL,
  privilegio INTEGER,
  tarjeta TEXT,
  grupo INTEGER,
  sn TEXT NOT NULL,          -- reloj que mandó el dato
  actualizado TEXT NOT NULL  -- timestamp de la PC al recibirlo
);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
  """Abre una conexión nueva (una por operación) y crea el esquema si falta.

  `path` permite apuntar a otra base (tests). Usar con `closing(connect())`.
  """
  conn = sqlite3.connect(path or DB_PATH, timeout=10)
  conn.row_factory = sqlite3.Row
  conn.executescript(_SCHEMA)
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


def upsert_empleados(sn: str, usuarios: list, path: Path | None = None) -> int:
  """Guarda los empleados que manda el reloj; si el PIN ya existe, actualiza sus datos.

  Devuelve cuántos registros se procesaron. Si algo falla no se guarda ninguno.
  """
  actualizado = datetime.now().isoformat(sep=" ", timespec="seconds")
  filas = [(u.pin, u.nombre, u.privilegio, u.tarjeta, u.grupo, sn, actualizado)
           for u in usuarios]
  with closing(connect(path)) as conn, conn:
    conn.executemany(
      "INSERT INTO empleados (pin, nombre, privilegio, tarjeta, grupo, sn, actualizado)"
      " VALUES (?, ?, ?, ?, ?, ?, ?)"
      " ON CONFLICT (pin) DO UPDATE SET nombre = excluded.nombre,"
      " privilegio = excluded.privilegio, tarjeta = excluded.tarjeta,"
      " grupo = excluded.grupo, sn = excluded.sn, actualizado = excluded.actualizado",
      filas,
    )
  return len(filas)


def listar_marcaciones(desde: str | None = None, hasta: str | None = None,
                       pin: str | None = None, limite: int = 500,
                       path: Path | None = None) -> tuple[list[sqlite3.Row], bool]:
  """Marcaciones más nuevas primero, con el nombre del empleado si existe.

  `desde`/`hasta`: fechas YYYY-MM-DD inclusivas. Devuelve (filas, truncado): `truncado` es
  True si había más de `limite` filas.
  """
  where, params = [], []
  if desde:
    where.append("m.fecha_hora >= ?")
    params.append(desde)
  if hasta:
    where.append("m.fecha_hora < date(?, '+1 day')")
    params.append(hasta)
  if pin:
    where.append("m.pin = ?")
    params.append(pin)
  sql = (
    "SELECT m.fecha_hora, m.pin, e.nombre, m.verificacion, m.sn"
    " FROM marcaciones m LEFT JOIN empleados e ON e.pin = m.pin"
    + (" WHERE " + " AND ".join(where) if where else "")  # solo fragmentos fijos con ?
    + " ORDER BY m.fecha_hora DESC, m.id DESC LIMIT ?"
  )
  with closing(connect(path)) as conn:
    filas = conn.execute(sql, [*params, limite + 1]).fetchall()
  return filas[:limite], len(filas) > limite


def listar_pins(path: Path | None = None) -> list[sqlite3.Row]:
  """PINs conocidos (empleados + los que aparecen en marcaciones) con su nombre si existe."""
  with closing(connect(path)) as conn:
    return conn.execute(
      "SELECT p.pin, e.nombre FROM"
      " (SELECT pin FROM empleados UNION SELECT pin FROM marcaciones) p"
      " LEFT JOIN empleados e ON e.pin = p.pin"
      " ORDER BY CAST(p.pin AS INTEGER), p.pin"
    ).fetchall()


def listar_empleados(path: Path | None = None) -> list[sqlite3.Row]:
  """Empleados con la cantidad de marcaciones de cada uno."""
  with closing(connect(path)) as conn:
    return conn.execute(
      "SELECT e.pin, e.nombre, e.privilegio, e.tarjeta, e.grupo, e.actualizado,"
      " COALESCE(c.total, 0) AS marcaciones"
      " FROM empleados e"
      " LEFT JOIN (SELECT pin, COUNT(*) AS total FROM marcaciones GROUP BY pin) c ON c.pin = e.pin"
      " ORDER BY CAST(e.pin AS INTEGER), e.pin"
    ).fetchall()
