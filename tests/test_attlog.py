import logging
import sqlite3
from contextlib import closing

from app import db
from app.iclock import parse_attlog
from conftest import fixture_text

SN = "TESTSN0001"
URL = f"/iclock/cdata?SN={SN}&table=ATTLOG&Stamp=9999"


def rows(path):
  with closing(db.connect(path)) as conn:
    return conn.execute("SELECT * FROM marcaciones ORDER BY fecha_hora").fetchall()


def test_parse_lote():
  m = parse_attlog(fixture_text("attlog_lote.txt"))
  assert len(m) == 14
  assert m[0].pin == "1"
  assert m[0].fecha_hora == "2026-10-13 15:39:37"
  assert (m[0].estado, m[0].verificacion) == (0, 15)
  assert m[0].raw == "1\t2026-10-13 15:39:37\t0\t15\t0\t0\t0\t0\t0\t0\t"
  assert m[-1].fecha_hora == "2026-10-13 17:59:46"


def test_parse_ignora_lineas_vacias():
  assert len(parse_attlog(fixture_text("attlog_tiempo_real.txt"))) == 1
  assert parse_attlog("") == []


def test_parse_salta_lineas_mal_formadas(caplog):
  # Fixture sintético: 2 líneas reales + 4 mal formadas agregadas a mano
  with caplog.at_level(logging.WARNING, logger="iclock"):
    m = parse_attlog(fixture_text("attlog_sintetico_con_basura.txt"))
  assert [x.fecha_hora for x in m] == ["2026-10-13 15:39:37", "2026-10-13 15:45:58"]
  assert len(caplog.records) == 4


def test_lote_repetido_no_duplica(db_path):
  m = parse_attlog(fixture_text("attlog_lote.txt"))
  assert db.insert_marcaciones(SN, m, db_path) == 14
  assert db.insert_marcaciones(SN, m, db_path) == 0
  assert len(rows(db_path)) == 14


def test_mismo_pin_y_hora_en_otro_reloj_es_otra_marcacion(db_path):
  m = parse_attlog(fixture_text("attlog_tiempo_real.txt"))
  assert db.insert_marcaciones(SN, m, db_path) == 1
  assert db.insert_marcaciones("TESTSN0002", m, db_path) == 1


def test_endpoint_guarda_y_responde_ok(client, db_path):
  r = client.post(URL, content=fixture_text("attlog_lote.txt"),
                  headers={"content-type": "text/plain"})
  assert (r.status_code, r.text) == (200, "OK")
  datos = rows(db_path)
  assert len(datos) == 14
  assert datos[0]["sn"] == SN and datos[0]["pin"] == "1"
  assert datos[0]["raw"].startswith("1\t2026-10-13 15:39:37")
  assert datos[0]["recibido"]
  # Reenvío del lote + una en tiempo real: solo la nueva se agrega
  client.post(URL, content=fixture_text("attlog_lote.txt"))
  client.post(URL, content=fixture_text("attlog_tiempo_real.txt"))
  assert len(rows(db_path)) == 15


def test_endpoint_con_basura_guarda_las_validas(client, db_path):
  r = client.post(URL, content=fixture_text("attlog_sintetico_con_basura.txt"))
  assert (r.status_code, r.text) == (200, "OK")
  assert len(rows(db_path)) == 2


def test_endpoint_guarda_sample_en_directorio_temporal(client, tmp_path):
  client.post(URL, content=fixture_text("attlog_tiempo_real.txt"))
  assert len(list(tmp_path.glob("*_POST_iclock_cdata.txt"))) == 1


def test_endpoint_error_de_base_no_responde_ok(client, monkeypatch):
  def falla(*args, **kwargs):
    raise sqlite3.OperationalError("disk I/O error")

  monkeypatch.setattr(db, "connect", falla)
  r = client.post(URL, content=fixture_text("attlog_tiempo_real.txt"))
  assert r.status_code == 500


def test_otras_rutas_siguen_respondiendo_ok(client, db_path):
  r = client.get("/iclock/getrequest?SN=TESTSN0001")
  assert (r.status_code, r.text) == (200, "OK")
  assert not db_path.exists()
