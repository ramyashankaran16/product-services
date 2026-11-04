from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.product_repository import ProductRepository
from app.services.health_service import HealthService
from app.services.product_service import ProductService


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(db))


def get_health_service(db: Session = Depends(get_db)) -> HealthService:
    return HealthService(db)
