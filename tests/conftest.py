import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db, iclock  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture_text(name: str) -> str:
  return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def db_path(tmp_path, monkeypatch):
  """Base y samples temporales: los tests nunca tocan los datos reales."""
  path = tmp_path / "test.db"
  monkeypatch.setattr(db, "DB_PATH", path)
  monkeypatch.setattr(iclock, "SAMPLES_DIR", tmp_path)
  return path


@pytest.fixture
def client(db_path):
  app = FastAPI()
  app.include_router(iclock.router)
  return TestClient(app)
