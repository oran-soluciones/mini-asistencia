"""Base SQLite: esquema y consultas (sqlite3 estándar, sin ORM)."""
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
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
  anulada TEXT,              -- timestamp de la PC si se anuló a mano (NULL: cuenta)
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
CREATE TABLE IF NOT EXISTS relojes (
  sn TEXT PRIMARY KEY,
  ultimo_contacto TEXT NOT NULL  -- último getrequest recibido
);
CREATE TABLE IF NOT EXISTS comandos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sn TEXT NOT NULL,          -- reloj destino
  pin TEXT NOT NULL,
  tipo TEXT NOT NULL,        -- alta | modificacion | baja
  texto TEXT NOT NULL,       -- comando sin el prefijo "C:<id>:"
  estado TEXT NOT NULL,      -- pendiente | enviado | ok | error
  codigo_retorno INTEGER,    -- Return= del reloj (NULL si no confirmó)
  intentos INTEGER NOT NULL DEFAULT 0,
  creado TEXT NOT NULL,
  enviado TEXT,              -- última entrega
  confirmado TEXT
);
CREATE INDEX IF NOT EXISTS idx_comandos_pin ON comandos (pin);
"""

# Un comando 'enviado' sin confirmación se vuelve a entregar a los REINTENTO_SEGUNDOS, hasta
# MAX_ENTREGAS veces; si tampoco así confirma pasa a 'error' (codigo_retorno NULL).
REINTENTO_SEGUNDOS = 120
MAX_ENTREGAS = 3


def ahora() -> datetime:
  """Hora de la PC (los tests la reemplazan para no esperar)."""
  return datetime.now()


def _ts(momento: datetime | None = None) -> str:
  return (momento or ahora()).isoformat(sep=" ", timespec="seconds")


def connect(path: Path | None = None) -> sqlite3.Connection:
  """Abre una conexión nueva (una por operación) y crea el esquema si falta.

  `path` permite apuntar a otra base (tests). Usar con `closing(connect())`.
  """
  conn = sqlite3.connect(path or DB_PATH, timeout=10)
  conn.row_factory = sqlite3.Row
  conn.executescript(_SCHEMA)
  _migrar(conn)
  return conn


def _migrar(conn: sqlite3.Connection) -> None:
  """Agrega las columnas nuevas a una base creada por una versión anterior."""
  columnas = {c["name"] for c in conn.execute("PRAGMA table_info(marcaciones)")}
  if "anulada" not in columnas:
    try:
      conn.execute("ALTER TABLE marcaciones ADD COLUMN anulada TEXT")
      conn.commit()
    except sqlite3.OperationalError:  # otra conexión la agregó al mismo tiempo
      pass


def insert_marcaciones(sn: str, marcaciones: list, path: Path | None = None) -> int:
  """Guarda las marcaciones; las repetidas (sn, pin, fecha_hora) se ignoran.

  Devuelve cuántas eran nuevas. Si algo falla no se guarda ninguna (transacción).
  """
  recibido = _ts()
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
  actualizado = _ts()
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
  """Marcaciones más nuevas primero (anuladas incluidas), con el nombre del empleado si existe.

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
    "SELECT m.id, m.fecha_hora, m.pin, e.nombre, m.verificacion, m.sn, m.anulada"
    " FROM marcaciones m LEFT JOIN empleados e ON e.pin = m.pin"
    + (" WHERE " + " AND ".join(where) if where else "")  # solo fragmentos fijos con ?
    + " ORDER BY m.fecha_hora DESC, m.id DESC LIMIT ?"
  )
  with closing(connect(path)) as conn:
    filas = conn.execute(sql, [*params, limite + 1]).fetchall()
  return filas[:limite], len(filas) > limite


def anular_marcacion(marcacion_id: int, anular: bool = True, path: Path | None = None) -> bool:
  """Anula (o restaura, con `anular=False`) una marcación. No se borra nunca: queda en la base
  para que el reloj no pueda volver a cargarla y para poder restaurarla.

  Devuelve False si no existe o ya estaba en ese estado.
  """
  with closing(connect(path)) as conn, conn:
    if anular:
      cur = conn.execute(
        "UPDATE marcaciones SET anulada = ? WHERE id = ? AND anulada IS NULL",
        (_ts(), marcacion_id))
    else:
      cur = conn.execute(
        "UPDATE marcaciones SET anulada = NULL WHERE id = ? AND anulada IS NOT NULL",
        (marcacion_id,))
    return cur.rowcount == 1


def listar_pins(path: Path | None = None) -> list[sqlite3.Row]:
  """PINs conocidos (empleados + los que aparecen en marcaciones) con su nombre si existe."""
  with closing(connect(path)) as conn:
    return conn.execute(
      "SELECT p.pin, e.nombre FROM"
      " (SELECT pin FROM empleados UNION SELECT pin FROM marcaciones) p"
      " LEFT JOIN empleados e ON e.pin = p.pin"
      " ORDER BY CAST(p.pin AS INTEGER), p.pin"
    ).fetchall()


_SQL_EMPLEADOS = (
  "SELECT e.pin, e.nombre, e.privilegio, e.tarjeta, e.grupo, e.sn, e.actualizado,"
  " COALESCE(m.total, 0) AS marcaciones,"
  " c.id AS cmd_id, c.tipo AS cmd_tipo, c.estado AS cmd_estado, c.codigo_retorno AS cmd_codigo,"
  " COALESCE(c.tipo = 'baja' AND c.estado IN ('pendiente', 'enviado'), 0) AS baja_pendiente"
  " FROM empleados e"
  " LEFT JOIN (SELECT pin, COUNT(*) AS total FROM marcaciones WHERE anulada IS NULL"
  " GROUP BY pin) m ON m.pin = e.pin"
  " LEFT JOIN comandos c ON c.id = (SELECT MAX(id) FROM comandos WHERE pin = e.pin)"
)


def listar_empleados(path: Path | None = None) -> list[sqlite3.Row]:
  """Empleados con la cantidad de marcaciones y el estado de su último comando."""
  with closing(connect(path)) as conn:
    return conn.execute(
      _SQL_EMPLEADOS + " ORDER BY CAST(e.pin AS INTEGER), e.pin"
    ).fetchall()


def obtener_empleado(pin: str, path: Path | None = None) -> sqlite3.Row | None:
  with closing(connect(path)) as conn:
    return conn.execute(_SQL_EMPLEADOS + " WHERE e.pin = ?", (pin,)).fetchone()


def registrar_contacto(sn: str, path: Path | None = None) -> None:
  """Anota que el reloj `sn` acaba de hacer un getrequest."""
  with closing(connect(path)) as conn, conn:
    conn.execute(
      "INSERT INTO relojes (sn, ultimo_contacto) VALUES (?, ?)"
      " ON CONFLICT (sn) DO UPDATE SET ultimo_contacto = excluded.ultimo_contacto",
      (sn, _ts()),
    )


def ultimo_reloj(path: Path | None = None) -> sqlite3.Row | None:
  """El reloj que hizo contacto más recientemente (sn, ultimo_contacto), o None."""
  with closing(connect(path)) as conn:
    return conn.execute(
      "SELECT sn, ultimo_contacto FROM relojes ORDER BY ultimo_contacto DESC, rowid DESC LIMIT 1"
    ).fetchone()


def _encolar(conn: sqlite3.Connection, sn: str, pin: str, tipo: str, texto: str) -> int:
  return conn.execute(
    "INSERT INTO comandos (sn, pin, tipo, texto, estado, creado)"
    " VALUES (?, ?, ?, ?, 'pendiente', ?)",
    (sn, pin, tipo, texto, _ts()),
  ).lastrowid


def encolar_comando(sn: str, pin: str, tipo: str, texto: str, path: Path | None = None) -> int:
  """Encola un comando para el reloj `sn` (estado 'pendiente'). Devuelve su id."""
  with closing(connect(path)) as conn, conn:
    return _encolar(conn, sn, pin, tipo, texto)


def guardar_empleado_y_encolar(tipo: str, sn: str, pin: str, nombre: str, privilegio: int,
                               texto: str, path: Path | None = None) -> int:
  """Alta ('alta': falla con ValueError si el PIN ya existe) o cambio ('modificacion') del
  empleado local, más el comando para el reloj, en una sola transacción. Devuelve el id."""
  with closing(connect(path)) as conn, conn:
    if tipo == "alta":
      try:
        conn.execute(
          "INSERT INTO empleados (pin, nombre, privilegio, tarjeta, grupo, sn, actualizado)"
          " VALUES (?, ?, ?, '', 1, ?, ?)",
          (pin, nombre, privilegio, sn, _ts()),
        )
      except sqlite3.IntegrityError:
        raise ValueError(f"el PIN {pin} ya existe") from None
    else:
      conn.execute(
        "UPDATE empleados SET nombre = ?, privilegio = ?, actualizado = ? WHERE pin = ?",
        (nombre, privilegio, _ts(), pin),
      )
    return _encolar(conn, sn, pin, tipo, texto)


def siguiente_comando(sn: str, path: Path | None = None) -> sqlite3.Row | None:
  """Toma el próximo comando para entregar al reloj `sn` y lo marca 'enviado'.

  Uno por vez y en orden: mientras haya uno 'enviado' de hace menos de REINTENTO_SEGUNDOS
  no se entrega otro. Pasado ese tiempo sin confirmación se reentrega; tras MAX_ENTREGAS
  entregas sin confirmar pasa a 'error' (sin código). Devuelve None si no hay nada.
  """
  momento = ahora()
  limite = _ts(momento - timedelta(seconds=REINTENTO_SEGUNDOS))
  with closing(connect(path)) as conn, conn:
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
      "UPDATE comandos SET estado = 'error' WHERE sn = ? AND estado = 'enviado'"
      " AND intentos >= ? AND enviado <= ?",
      (sn, MAX_ENTREGAS, limite),
    )
    en_vuelo = conn.execute(
      "SELECT 1 FROM comandos WHERE sn = ? AND estado = 'enviado' AND enviado > ?", (sn, limite)
    ).fetchone()
    if en_vuelo:
      return None
    filas = conn.execute(
      "UPDATE comandos SET estado = 'enviado', enviado = ?, intentos = intentos + 1"
      " WHERE id = (SELECT MIN(id) FROM comandos WHERE sn = ? AND estado IN ('pendiente', 'enviado'))"
      " RETURNING *",
      (_ts(momento), sn),
    ).fetchall()  # completo: la transacción no puede cerrarse con el statement a medias
    return filas[0] if filas else None


def confirmar_comando(cmd_id: int, codigo: int, path: Path | None = None) -> bool:
  """Registra la respuesta del reloj (Return=`codigo`: 0 = OK). Una baja OK borra al empleado.

  Acepta comandos 'enviado' o 'error' (confirmación tardía). Devuelve False si no existe o
  no estaba esperando confirmación (p. ej. ya confirmado).
  """
  with closing(connect(path)) as conn, conn:
    fila = conn.execute(
      "SELECT tipo, pin FROM comandos WHERE id = ? AND estado IN ('enviado', 'error')", (cmd_id,)
    ).fetchone()
    if fila is None:
      return False
    conn.execute(
      "UPDATE comandos SET estado = ?, codigo_retorno = ?, confirmado = ? WHERE id = ?",
      ("ok" if codigo == 0 else "error", codigo, _ts(), cmd_id),
    )
    if codigo == 0 and fila["tipo"] == "baja":
      conn.execute("DELETE FROM empleados WHERE pin = ?", (fila["pin"],))
    return True


def listar_comandos(limite: int = 20, path: Path | None = None) -> list[sqlite3.Row]:
  """Últimos comandos, el más nuevo primero."""
  with closing(connect(path)) as conn:
    return conn.execute(
      "SELECT id, sn, pin, tipo, estado, codigo_retorno, intentos, creado, enviado, confirmado"
      " FROM comandos ORDER BY id DESC LIMIT ?", (limite,)
    ).fetchall()
