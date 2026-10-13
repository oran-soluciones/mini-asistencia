import logging
import sqlite3
from contextlib import closing

from app import db
from app.iclock import parse_users
from conftest import fixture_text

SN = "TESTSN0001"
URL = f"/iclock/cdata?SN={SN}&table=OPERLOG&OpStamp=9999"
PASSWDS = ("0000", "4821")  # los Passwd ficticios del fixture


def rows(path):
  with closing(db.connect(path)) as conn:
    return conn.execute("SELECT * FROM empleados ORDER BY pin").fetchall()


def test_parse_users_solo_lineas_user():
  u = parse_users(fixture_text("operlog_usuarios.txt"))
  assert [x.pin for x in u] == ["7", "8"]
  assert (u[0].nombre, u[0].privilegio, u[0].tarjeta, u[0].grupo) == ("Ana Gómez", 0, "", 1)
  assert (u[1].nombre, u[1].privilegio, u[1].tarjeta, u[1].grupo) == ("Luis Pérez", 14, "1234567", 1)


def test_parse_users_sin_usuarios():
  assert parse_users("") == []
  assert parse_users("OPLOG 4\t0\t2026-10-13 09:00:10\t1\t0\t0\t0\n") == []


def test_parse_users_salta_mal_formadas_sin_loguear_passwd(caplog):
  body = (
    "USER Name=sin pin\tPasswd=4821\n"
    "USER PIN=\tName=pin vacio\tPasswd=4821\n"
    "USER PIN=9\tName=Bien\tPri=x\tPasswd=4821\tbasura\tGrp=\n"
  )
  with caplog.at_level(logging.WARNING, logger="iclock"):
    u = parse_users(body)
  assert [(x.pin, x.nombre, x.privilegio, x.grupo) for x in u] == [("9", "Bien", None, None)]
  assert len(caplog.records) == 2
  assert "4821" not in caplog.text


def test_upsert_guarda_y_actualiza_nombre(db_path):
  u = parse_users(fixture_text("operlog_usuarios.txt"))
  assert db.upsert_empleados(SN, u, db_path) == 2
  assert [r["nombre"] for r in rows(db_path)] == ["Ana Gómez", "Luis Pérez"]
  # El reloj vuelve a mandar el PIN 7 con otro nombre y privilegio
  cambio = parse_users("USER PIN=7\tName=Ana G. de Díaz\tPri=14\tPasswd=0000\tCard=55\tGrp=2\n")
  db.upsert_empleados(SN, cambio, db_path)
  datos = rows(db_path)
  assert len(datos) == 2
  assert (datos[0]["nombre"], datos[0]["privilegio"], datos[0]["tarjeta"], datos[0]["grupo"]) == (
    "Ana G. de Díaz", 14, "55", 2)


def test_no_se_guarda_passwd(client, db_path):
  client.post(URL, content=fixture_text("operlog_usuarios.txt"))
  with closing(db.connect(db_path)) as conn:
    columnas = [c["name"].lower() for c in conn.execute("PRAGMA table_info(empleados)")]
    todo = conn.execute("SELECT * FROM empleados").fetchall()
  assert not any("pass" in c for c in columnas)
  for fila in todo:
    for valor in PASSWDS:
      assert valor not in repr(tuple(fila))


def test_endpoint_operlog_guarda_empleados_y_responde_ok(client, db_path):
  r = client.post(URL, content=fixture_text("operlog_usuarios.txt"),
                  headers={"content-type": "text/plain"})
  assert (r.status_code, r.text) == (200, "OK")
  datos = rows(db_path)
  assert [(d["pin"], d["nombre"], d["sn"]) for d in datos] == [
    ("7", "Ana Gómez", SN), ("8", "Luis Pérez", SN)]
  assert datos[0]["actualizado"]
  # Reenvío: no duplica
  client.post(URL, content=fixture_text("operlog_usuarios.txt"))
  assert len(rows(db_path)) == 2


def test_operlog_solo_oplog_no_toca_la_base(client, db_path):
  r = client.post(URL, content="OPLOG 4\t0\t2026-10-13 09:00:10\t1\t0\t0\t0\n")
  assert (r.status_code, r.text) == (200, "OK")
  assert not db_path.exists()


def test_operlog_error_de_base_no_responde_ok(client, monkeypatch):
  def falla(*args, **kwargs):
    raise sqlite3.OperationalError("disk I/O error")

  monkeypatch.setattr(db, "connect", falla)
  r = client.post(URL, content=fixture_text("operlog_usuarios.txt"))
  assert r.status_code == 500
