
import os

# Must be set before the app is imported; never points at a real database.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    return cfg


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    cfg = alembic_config()
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def app(engine):
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def product_payload():
    return {
        "name": "Wireless Mouse",
        "description": "Ergonomic 2.4GHz mouse",
        "price": 19.99,
        "quantity": 50,
        "category": "Electronics",
    }


@pytest.fixture
def create_product(client, product_payload):
    """Factory: create a product via the API and return its JSON."""

    def _create(**overrides):
        body = {**product_payload, **overrides}
        response = client.post("/api/v1/products", json=body)
        assert response.status_code == 201, response.text
        return response.json()

    return _create
