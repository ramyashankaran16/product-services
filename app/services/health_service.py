
import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def database_is_up(self) -> bool:
        try:
            self._db.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            logger.exception("Database health check failed")
            return False
