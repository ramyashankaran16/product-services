from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.dependencies import get_product_service
from app.models.product import ProductStatus
from app.schemas.error import ErrorResponse
from app.schemas.product import (
    ProductCreate,
    ProductListQuery,
    ProductPage,
    ProductPatch,
    ProductReplace,
    ProductResponse,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["products"])

_400 = {400: {"model": ErrorResponse, "description": "Validation failed or malformed request"}}
_404 = {404: {"model": ErrorResponse, "description": "Product not found"}}
_409 = {409: {"model": ErrorResponse, "description": "Duplicate product name"}}


@router.post("", status_code=201, response_model=ProductResponse, responses={**_400, **_409})
def create_product(
    payload: ProductCreate,
    request: Request,
    response: Response,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    product = service.create(payload)
    response.headers["Location"] = str(request.url_for("get_product", product_id=str(product.id)))
    return product


@router.get("", response_model=ProductPage, responses=_400)
def list_products(
    page: int = Query(1, ge=1, description="Page number, starting at 1"),
    size: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
    category: str | None = Query(None, max_length=50, description="Exact category, case-insensitive"),
    status: ProductStatus | None = Query(None),
    min_price: Decimal | None = Query(None, alias="minPrice", ge=0),
    max_price: Decimal | None = Query(None, alias="maxPrice", ge=0),
    sort: str | None = Query(None, description="e.g. price,asc or name,desc (default createdAt,desc)"),
    service: ProductService = Depends(get_product_service),
) -> ProductPage:
    query = ProductListQuery(
        page=page,
        size=size,
        category=category,
        status=status,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
    )
    return service.list(query)


@router.get("/{product_id}", name="get_product", response_model=ProductResponse, responses={**_400, **_404})
def get_product(product_id: UUID, service: ProductService = Depends(get_product_service)) -> ProductResponse:
    return service.get(product_id)


@router.put("/{product_id}", response_model=ProductResponse, responses={**_400, **_404, **_409})
def replace_product(
    product_id: UUID,
    payload: ProductReplace,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    return service.replace(product_id, payload)


@router.patch("/{product_id}", response_model=ProductResponse, responses={**_400, **_404, **_409})
def patch_product(
    product_id: UUID,
    payload: ProductPatch,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    return service.patch(product_id, payload)


@router.delete("/{product_id}", status_code=204, responses={**_400, **_404})
def delete_product(product_id: UUID, service: ProductService = Depends(get_product_service)) -> Response:
    service.delete(product_id)
    return Response(status_code=204)
