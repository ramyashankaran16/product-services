
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.models.product import Product, ProductStatus


SORT_COLUMNS = {
    "name": Product.name,
    "price": Product.price,
    "quantity": Product.quantity,
    "category": Product.category,
    "createdAt": Product.created_at,
    "updatedAt": Product.updated_at,
}
SORTABLE_FIELDS = tuple(SORT_COLUMNS)

@dataclass(frozen=True)
class ProductFilters:
    category: str | None = None
    status: ProductStatus | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, product_id: UUID) -> Product | None:
        return self._db.get(Product, product_id)

    def find_by_name(self, name: str, exclude_id: UUID | None = None) -> Product | None:
       
        stmt = select(Product).where(func.lower(Product.name) == name.lower())
        if exclude_id is not None:
            stmt = stmt.where(Product.id != exclude_id)
        return self._db.scalars(stmt).first()

    def save(self, product: Product) -> Product:
        self._db.add(product)
        self._db.commit()
        self._db.refresh(product)
        return product

    def delete(self, product: Product) -> None:
        self._db.delete(product)
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()

    def search(
        self,
        filters: ProductFilters,
        sort_field: str,
        sort_direction: str,
        offset: int,
        limit: int,
    ) -> tuple[list[Product], int]:
        stmt = select(Product)
        if filters.category:
            stmt = stmt.where(func.lower(Product.category) == filters.category.lower())
        if filters.status:
            stmt = stmt.where(Product.status == filters.status)
        if filters.min_price is not None:
            stmt = stmt.where(Product.price >= filters.min_price)
        if filters.max_price is not None:
            stmt = stmt.where(Product.price <= filters.max_price)

        total = self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        order = desc if sort_direction == "desc" else asc
        
        stmt = stmt.order_by(order(SORT_COLUMNS[sort_field]), Product.id).offset(offset).limit(limit)
        return list(self._db.scalars(stmt).all()), total
