from alembic import command
from sqlalchemy import create_engine, inspect, text

from tests.conftest import alembic_config


def test_upgrade_and_downgrade(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migrate.db'}")
    cfg = alembic_config()

    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    inspector = inspect(engine)
    assert "products" in inspector.get_table_names()
    with engine.connect() as connection:  # read sqlite_master: expression indexes are not reflected
        index_names = set(
            connection.scalars(text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='products'"))
        )
    assert {"uq_products_name_lower", "ix_products_category", "ix_products_status"} <= index_names

    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, "base")
    assert "products" not in inspect(engine).get_table_names()
