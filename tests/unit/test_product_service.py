
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions.errors import BadRequestError, ConflictError, NotFoundError
from app.models.product import Product, ProductStatus
from app.repositories.product_repository import ProductFilters
from app.schemas.product import ProductCreate, ProductListQuery, ProductPatch, ProductReplace
from app.services.product_service import ProductService


def make_product(**overrides) -> Product:
    now = datetime.now(timezone.utc)
    values = {
        "id": uuid.uuid4(),
        "name": "Keyboard",
        "description": None,
        "price": Decimal("49.90"),
        "quantity": 10,
        "category": "Electronics",
        "status": ProductStatus.ACTIVE,
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return Product(**values)


def _fake_save(product: Product) -> Product:
    now = datetime.now(timezone.utc)
    product.id = product.id or uuid.uuid4()
    product.created_at = product.created_at or now
    product.updated_at = now
    return product


@pytest.fixture
def repo():
    repository = MagicMock()
    repository.find_by_name.return_value = None
    repository.save.side_effect = _fake_save
    return repository


@pytest.fixture
def service(repo):
    return ProductService(repo)


def create_dto(**overrides) -> ProductCreate:
    data = {"name": "Keyboard", "price": 49.9, "quantity": 10, "category": "Electronics"}
    data.update(overrides)
    return ProductCreate(**data)




def test_create_returns_dto_with_defaults(service, repo):
    result = service.create(create_dto(name="  Keyboard  "))

    assert result.name == "Keyboard"  # trimmed
    assert result.status == ProductStatus.ACTIVE
    assert result.id is not None
    repo.find_by_name.assert_called_once_with("Keyboard", exclude_id=None)
    repo.save.assert_called_once()


def test_create_rejects_duplicate_name(service, repo):
    repo.find_by_name.return_value = make_product()

    with pytest.raises(ConflictError) as exc_info:
        service.create(create_dto())

    assert exc_info.value.details[0]["field"] == "name"
    repo.save.assert_not_called()


def test_create_maps_integrity_error_to_conflict(service, repo):
    repo.save.side_effect = IntegrityError("INSERT", {}, Exception("unique violation"))

    with pytest.raises(ConflictError):
        service.create(create_dto())

    repo.rollback.assert_called_once()



def test_get_returns_product(service, repo):
    product = make_product()
    repo.get_by_id.return_value = product

    assert service.get(product.id).id == product.id


def test_get_unknown_id_raises_not_found(service, repo):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        service.get(uuid.uuid4())




def test_replace_overwrites_all_fields(service, repo):
    product = make_product(description="old")
    repo.get_by_id.return_value = product
    dto = ProductReplace(name="Keyboard Pro", price=79.5, quantity=3, category="Accessories", status="INACTIVE")

    result = service.replace(product.id, dto)

    assert result.name == "Keyboard Pro"
    assert result.description is None  # omitted optional field is reset
    assert result.status == ProductStatus.INACTIVE
    repo.find_by_name.assert_called_once_with("Keyboard Pro", exclude_id=product.id)


def test_replace_unknown_id_raises_not_found(service, repo):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        service.replace(uuid.uuid4(), ProductReplace(name="Abc", price=1, quantity=0, category="Cat"))


def test_replace_with_taken_name_raises_conflict(service, repo):
    repo.get_by_id.return_value = make_product()
    repo.find_by_name.return_value = make_product(name="Taken")

    with pytest.raises(ConflictError):
        service.replace(uuid.uuid4(), ProductReplace(name="Taken", price=1, quantity=0, category="Cat"))



def test_patch_changes_only_sent_fields(service, repo):
    product = make_product(description="keep me")
    repo.get_by_id.return_value = product

    result = service.patch(product.id, ProductPatch(price=10))

    assert result.price == Decimal("10")
    assert result.name == "Keyboard"
    assert result.description == "keep me"
    repo.find_by_name.assert_not_called()


def test_patch_with_name_checks_uniqueness(service, repo):
    repo.get_by_id.return_value = make_product()
    repo.find_by_name.return_value = make_product(name="Mouse")

    with pytest.raises(ConflictError):
        service.patch(uuid.uuid4(), ProductPatch(name="Mouse"))


def test_patch_with_empty_body_is_rejected(service, repo):
    with pytest.raises(BadRequestError):
        service.patch(uuid.uuid4(), ProductPatch())
    repo.get_by_id.assert_not_called()


def test_patch_unknown_id_raises_not_found(service, repo):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        service.patch(uuid.uuid4(), ProductPatch(quantity=1))




def test_delete_removes_product(service, repo):
    product = make_product()
    repo.get_by_id.return_value = product

    service.delete(product.id)

    repo.delete.assert_called_once_with(product)


def test_delete_unknown_id_raises_not_found(service, repo):
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        service.delete(uuid.uuid4())
    repo.delete.assert_not_called()




def test_list_builds_page_metadata(service, repo):
    repo.search.return_value = ([make_product(), make_product(name="B")], 25)

    page = service.list(ProductListQuery(page=3, size=10, category="  Electronics ", sort="price,desc"))

    assert page.total_items == 25
    assert page.total_pages == 3
    assert len(page.items) == 2
    filters, field, direction = repo.search.call_args.args
    assert filters == ProductFilters(category="Electronics")
    assert (field, direction) == ("price", "desc")
    assert repo.search.call_args.kwargs == {"offset": 20, "limit": 10}


def test_list_empty_has_zero_pages(service, repo):
    repo.search.return_value = ([], 0)

    page = service.list(ProductListQuery())

    assert page.total_pages == 0
    assert page.items == []


def test_list_rejects_min_price_above_max_price(service, repo):
    with pytest.raises(BadRequestError):
        service.list(ProductListQuery(min_price=Decimal("50"), max_price=Decimal("10")))
    repo.search.assert_not_called()


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, ("createdAt", "desc")),
        ("", ("createdAt", "desc")),
        ("price", ("price", "asc")),
        ("name,DESC", ("name", "desc")),
        (" price , asc ", ("price", "asc")),
    ],
)
def test_parse_sort_valid(raw, expected):
    assert ProductService.parse_sort(raw) == expected


@pytest.mark.parametrize("raw", ["colour,asc", "price,up", "price,asc,extra", ",asc"])
def test_parse_sort_invalid(raw):
    with pytest.raises(BadRequestError):
        ProductService.parse_sort(raw)
