import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, db, iclock, panel  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture_text(name: str) -> str:
  return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def db_path(tmp_path, monkeypatch):
  """Base, samples y carpeta de datos temporales: los tests nunca tocan los datos reales."""
  path = tmp_path / "test.db"
  monkeypatch.setattr(db, "DB_PATH", path)
  monkeypatch.setattr(iclock, "SAMPLES_DIR", tmp_path)
  datos = tmp_path / "datos"  # nombre y logo del colegio (colegio.json, logo.*)
  datos.mkdir()
  monkeypatch.setattr(config, "DATA_DIR", datos)
  return path


def crear_cliente(direccion):
  app = FastAPI()
  panel.instalar(app)  # mismo orden que main.py: el panel antes que el comodín de iclock
  app.include_router(iclock.router)
  return TestClient(app, client=direccion)


@pytest.fixture
def client(db_path):
  """Cliente local (127.0.0.1): ve el panel y /iclock."""
  return crear_cliente(("127.0.0.1", 50000))


@pytest.fixture
def client_externo(db_path):
  """Cliente de otra máquina de la red (como el reloj): solo /iclock."""
  return crear_cliente(("192.168.0.50", 1234))
