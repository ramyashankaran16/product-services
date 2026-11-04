
import logging
import math
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.exceptions.errors import BadRequestError, ConflictError, NotFoundError
from app.models.product import Product
from app.repositories.product_repository import SORTABLE_FIELDS, ProductFilters, ProductRepository
from app.schemas.product import (
    ProductCreate,
    ProductListQuery,
    ProductPage,
    ProductPatch,
    ProductReplace,
    ProductResponse,
)

logger = logging.getLogger(__name__)

DEFAULT_SORT = ("createdAt", "desc")
SORT_DIRECTIONS = ("asc", "desc")


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    
    def get(self, product_id: UUID) -> ProductResponse:
        return ProductResponse.model_validate(self._get_or_raise(product_id))

    def list(self, query: ProductListQuery) -> ProductPage:
        if query.min_price is not None and query.max_price is not None and query.min_price > query.max_price:
            raise BadRequestError(
                "Invalid price range",
                [{"field": "minPrice", "issue": "must be less than or equal to maxPrice"}],
            )
        sort_field, sort_direction = self.parse_sort(query.sort)
        filters = ProductFilters(
            category=query.category.strip() if query.category else None,
            status=query.status,
            min_price=query.min_price,
            max_price=query.max_price,
        )
        items, total = self._repository.search(
            filters,
            sort_field,
            sort_direction,
            offset=(query.page - 1) * query.size,
            limit=query.size,
        )
        return ProductPage(
            items=[ProductResponse.model_validate(p) for p in items],
            page=query.page,
            size=query.size,
            total_items=total,
            total_pages=math.ceil(total / query.size) if total else 0,
        )

    

    def create(self, data: ProductCreate) -> ProductResponse:
        self._ensure_name_available(data.name)
        product = self._save(Product(**data.model_dump()))
        logger.info("Product created id=%s name=%r", product.id, product.name)
        return ProductResponse.model_validate(product)

    def replace(self, product_id: UUID, data: ProductReplace) -> ProductResponse:
        product = self._get_or_raise(product_id)
        self._ensure_name_available(data.name, exclude_id=product_id)
        for field, value in data.model_dump().items():
            setattr(product, field, value)
        product = self._save(product)
        logger.info("Product replaced id=%s", product.id)
        return ProductResponse.model_validate(product)

    def patch(self, product_id: UUID, data: ProductPatch) -> ProductResponse:
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise BadRequestError(
                "Validation failed",
                [{"field": "body", "issue": "must contain at least one field to update"}],
            )
        product = self._get_or_raise(product_id)
        if "name" in changes:
            self._ensure_name_available(changes["name"], exclude_id=product_id)
        for field, value in changes.items():
            setattr(product, field, value)
        product = self._save(product)
        logger.info("Product patched id=%s fields=%s", product.id, sorted(changes))
        return ProductResponse.model_validate(product)

    def delete(self, product_id: UUID) -> None:
        product = self._get_or_raise(product_id)
        self._repository.delete(product)
        logger.info("Product deleted id=%s", product_id)

    

    @staticmethod
    def parse_sort(raw: str | None) -> tuple[str, str]:
        """Turn 'price,asc' into ('price', 'asc'). Direction defaults to asc."""
        if raw is None or not raw.strip():
            return DEFAULT_SORT
        parts = [p.strip() for p in raw.split(",")]
        field = parts[0]
        direction = parts[1].lower() if len(parts) > 1 else "asc"
        if len(parts) > 2 or field not in SORTABLE_FIELDS:
            raise BadRequestError(
                "Invalid sort parameter",
                [{"field": "sort", "issue": f"must be '<field>,<asc|desc>' where field is one of: {', '.join(SORTABLE_FIELDS)}"}],
            )
        if direction not in SORT_DIRECTIONS:
            raise BadRequestError(
                "Invalid sort parameter",
                [{"field": "sort", "issue": "direction must be 'asc' or 'desc'"}],
            )
        return field, direction

    def _get_or_raise(self, product_id: UUID) -> Product:
        product = self._repository.get_by_id(product_id)
        if product is None:
            raise NotFoundError(f"Product with id '{product_id}' was not found")
        return product

    def _ensure_name_available(self, name: str, exclude_id: UUID | None = None) -> None:
        if self._repository.find_by_name(name, exclude_id=exclude_id) is not None:
            raise ConflictError(
                "Product name already exists",
                [{"field": "name", "issue": f"a product named '{name}' already exists"}],
            )

    def _save(self, product: Product) -> Product:
        try:
            return self._repository.save(product)
        except IntegrityError as exc:
            # Safety net for a race: two requests passed the name check at the same time.
            self._repository.rollback()
            logger.warning("Integrity error while saving product name=%r: %s", product.name, exc.orig)
            raise ConflictError(
                "Product name already exists",
                [{"field": "name", "issue": f"a product named '{product.name}' already exists"}],
            ) from exc
