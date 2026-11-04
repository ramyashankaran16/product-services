
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    field_serializer,
    field_validator,
)
from pydantic.alias_generators import to_camel

from app.models.product import ProductStatus


def _require_number(value: Any) -> Any:
    
    if value is None:
        raise ValueError("must not be null")
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("must be a number")
    return value



NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100, strict=True)]
DescriptionStr = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500, strict=True)]
CategoryStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=50, strict=True)]
Price = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=2),
    BeforeValidator(_require_number),
    PlainSerializer(float, return_type=float, when_used="json"),
]
Quantity = Annotated[int, Field(ge=0, le=2_147_483_647, strict=True)]


class _RequestModel(BaseModel):
    
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class ProductCreate(_RequestModel):
    name: NameStr
    description: DescriptionStr | None = None
    price: Price
    quantity: Quantity
    category: CategoryStr
    status: ProductStatus = ProductStatus.ACTIVE

    @field_validator("description")
    @classmethod
    def _blank_description_to_none(cls, value: str | None) -> str | None:
        return value or None



    

class ProductPatch(_RequestModel):
    

    
    name: NameStr = None  
    description: DescriptionStr | None = None
    price: Price = None  
    quantity: Quantity = None  
    category: CategoryStr = None  
    status: ProductStatus = None  

    @field_validator("description")
    @classmethod
    def _blank_description_to_none(cls, value: str | None) -> str | None:
        return value or None


class ProductResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    id: UUID
    name: str
    description: str | None
    price: Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
    quantity: int
    category: str
    status: ProductStatus
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _serialize_utc(self, value: datetime) -> str:
        if value.tzinfo is None:  # some databases (e.g. SQLite) drop the zone
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ProductPage(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[ProductResponse]
    page: int
    size: int
    total_items: int
    total_pages: int


class ProductListQuery(BaseModel):
    

    page: int = 1
    size: int = 10
    category: str | None = None
    status: ProductStatus | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    sort: str | None = None
