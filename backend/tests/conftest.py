from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_ROOT = Path(tempfile.mkdtemp(prefix="food_optimizer_backend_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}"
os.environ["LOG_LEVEL"] = "WARNING"

import pytest
from fastapi.testclient import TestClient

from backend.app.db import models  # noqa: F401
from backend.app.db.base import Base
from backend.app.db.session import SessionLocal, engine
from backend.app.main import app
from backend.app.services.data_service import generate_dataset
from backend.app.services.forecasting import train_from_generated_data

Base.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def clean_database():
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    yield


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def generated_dataset():
    result = generate_dataset(months=2, seed=42, residents=200, validate_after=True)
    assert result["validation"]["ok"], result["validation"]
    model = train_from_generated_data()
    return {"dataset": result, "model": model}


@pytest.fixture()
def synced_client(client, generated_dataset):
    response = client.post("/api/v1/data/sync")
    assert response.status_code == 200, response.text
    return client


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
