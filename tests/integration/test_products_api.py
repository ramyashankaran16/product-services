
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_product_service

BASE = "/api/v1/products"
ERROR_KEYS = {"timestamp", "status", "error", "message", "path", "details"}


def assert_error(response, status, message=None):
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == ERROR_KEYS
    assert body["status"] == status
    assert body["timestamp"].endswith("Z")
    if message:
        assert body["message"] == message
    return body


def fields(body):
    return {d["field"] for d in body["details"]}




def test_health_returns_up(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP", "database": "UP"}


def test_health_reports_down_when_database_unreachable(app):
    from app.api.dependencies import get_health_service

    class Down:
        def database_is_up(self):
            return False

    app.dependency_overrides[get_health_service] = lambda: Down()
    with TestClient(app) as c:
        response = c.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "DOWN"




def test_create_returns_201_with_location(client, product_payload):
    response = client.post(BASE, json={**product_payload, "name": "  Wireless Mouse  "})

    assert response.status_code == 201
    body = response.json()
    assert response.headers["Location"].endswith(f"{BASE}/{body['id']}")
    assert body["name"] == "Wireless Mouse"
    assert body["price"] == 19.99
    assert body["status"] == "ACTIVE"
    assert body["createdAt"].endswith("Z") and body["updatedAt"].endswith("Z")
    assert "created_at" not in body


def test_create_missing_required_fields(client):
    body = assert_error(client.post(BASE, json={}), 400, "Validation failed")
    assert fields(body) == {"name", "price", "quantity", "category"}


@pytest.mark.parametrize(
    "override, field",
    [
        ({"price": 0}, "price"),
        ({"price": -5}, "price"),
        ({"price": 10.999}, "price"),
        ({"price": "10"}, "price"),
        ({"quantity": -1}, "quantity"),
        ({"quantity": "five"}, "quantity"),
        ({"quantity": 1.5}, "quantity"),
        ({"name": "A"}, "name"),
        ({"name": "   A   "}, "name"),
        ({"name": "x" * 101}, "name"),
        ({"name": 123}, "name"),
        ({"description": "d" * 501}, "description"),
        ({"category": "C"}, "category"),
        ({"category": "c" * 51}, "category"),
        ({"status": "DELETED"}, "status"),
        ({"id": str(uuid.uuid4())}, "id"),
        ({"createdAt": "2020-01-01T00:00:00Z"}, "createdAt"),
    ],
)
def test_create_rejects_invalid_values(client, product_payload, override, field):
    body = assert_error(client.post(BASE, json={**product_payload, **override}), 400)
    assert field in fields(body)


def test_create_malformed_json(client):
    response = client.post(BASE, content="{bad json", headers={"Content-Type": "application/json"})
    assert_error(response, 400, "Malformed JSON request body")


def test_create_duplicate_name_case_insensitive(client, create_product, product_payload):
    create_product()
    response = client.post(BASE, json={**product_payload, "name": "WIRELESS mouse"})
    assert_error(response, 409, "Product name already exists")



def test_get_by_id(client, create_product):
    created = create_product()
    response = client.get(f"{BASE}/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_id_returns_404(client):
    assert_error(client.get(f"{BASE}/{uuid.uuid4()}"), 404)


def test_get_malformed_id_returns_400(client):
    body = assert_error(client.get(f"{BASE}/not-a-uuid"), 400)
    assert body["details"] == [{"field": "id", "issue": "must be a valid UUID"}]




@pytest.fixture
def catalogue(create_product):
    create_product(name="Laptop", price=999.99, category="Electronics")
    create_product(name="Phone", price=599.00, category="Electronics")
    create_product(name="Cable", price=9.50, category="electronics", status="INACTIVE")
    create_product(name="Desk", price=250.00, category="Furniture")
    create_product(name="Chair", price=120.00, category="Furniture")


def test_list_default_pagination(client, catalogue):
    body = client.get(BASE).json()
    assert body["page"] == 1
    assert body["size"] == 10
    assert body["totalItems"] == 5
    assert body["totalPages"] == 1
    assert len(body["items"]) == 5


def test_list_paginates(client, catalogue):
    body = client.get(BASE, params={"page": 2, "size": 2, "sort": "name,asc"}).json()
    assert [p["name"] for p in body["items"]] == ["Desk", "Laptop"]
    assert body["totalPages"] == 3


def test_list_page_beyond_range_is_empty(client, catalogue):
    body = client.get(BASE, params={"page": 99}).json()
    assert body["items"] == []
    assert body["totalItems"] == 5


def test_list_filters_and_sorts_together(client, catalogue):
    params = {"category": "electronics", "status": "ACTIVE", "minPrice": 100, "maxPrice": 1000, "sort": "price,desc"}
    body = client.get(BASE, params=params).json()
    assert [p["name"] for p in body["items"]] == ["Laptop", "Phone"]
    assert body["totalItems"] == 2


def test_list_filter_by_status(client, catalogue):
    body = client.get(BASE, params={"status": "INACTIVE"}).json()
    assert [p["name"] for p in body["items"]] == ["Cable"]


@pytest.mark.parametrize(
    "params, field",
    [
        ({"size": 101}, "size"),
        ({"size": 0}, "size"),
        ({"page": 0}, "page"),
        ({"page": "abc"}, "page"),
        ({"status": "GONE"}, "status"),
        ({"minPrice": "cheap"}, "minPrice"),
        ({"sort": "colour,asc"}, "sort"),
        ({"sort": "price,sideways"}, "sort"),
        ({"minPrice": 50, "maxPrice": 10}, "minPrice"),
    ],
)
def test_list_rejects_bad_parameters(client, params, field):
    body = assert_error(client.get(BASE, params=params), 400)
    assert field in fields(body)



def test_put_replaces_product(client, create_product):
    created = create_product()
    replacement = {"name": "Gaming Mouse", "price": 59.5, "quantity": 5, "category": "Gaming", "status": "INACTIVE"}

    response = client.put(f"{BASE}/{created['id']}", json=replacement)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Gaming Mouse"
    assert body["description"] is None
    assert body["createdAt"] == created["createdAt"]
    assert body["updatedAt"] >= created["updatedAt"]


def test_put_keeping_own_name_is_allowed(client, create_product, product_payload):
    created = create_product()
    response = client.put(f"{BASE}/{created['id']}", json={**product_payload, "quantity": 1})
    assert response.status_code == 200


def test_put_requires_full_body(client, create_product):
    created = create_product()
    body = assert_error(client.put(f"{BASE}/{created['id']}", json={"name": "Only Name"}), 400)
    assert {"price", "quantity", "category"} <= fields(body)


def test_put_unknown_id_returns_404(client, product_payload):
    assert_error(client.put(f"{BASE}/{uuid.uuid4()}", json=product_payload), 404)


def test_put_duplicate_name_returns_409(client, create_product, product_payload):
    create_product(name="Taken Name")
    other = create_product(name="Other")
    response = client.put(f"{BASE}/{other['id']}", json={**product_payload, "name": "taken name"})
    assert_error(response, 409)



def test_patch_updates_only_given_fields(client, create_product):
    created = create_product()
    response = client.patch(f"{BASE}/{created['id']}", json={"price": 15.0})

    assert response.status_code == 200
    body = response.json()
    assert body["price"] == 15.0
    assert body["name"] == created["name"]
    assert body["description"] == created["description"]


def test_patch_can_clear_description(client, create_product):
    created = create_product()
    body = client.patch(f"{BASE}/{created['id']}", json={"description": None}).json()
    assert body["description"] is None


def test_patch_rejects_null_required_field(client, create_product):
    created = create_product()
    body = assert_error(client.patch(f"{BASE}/{created['id']}", json={"name": None, "price": None}), 400)
    assert {"name": "must not be null"}.items() <= {d["field"]: d["issue"] for d in body["details"]}.items()
    assert "price" in fields(body)


def test_patch_rejects_empty_body(client, create_product):
    created = create_product()
    assert_error(client.patch(f"{BASE}/{created['id']}", json={}), 400)


def test_patch_rejects_server_managed_fields(client, create_product):
    created = create_product()
    body = assert_error(client.patch(f"{BASE}/{created['id']}", json={"updatedAt": "2020-01-01T00:00:00Z"}), 400)
    assert fields(body) == {"updatedAt"}


def test_patch_unknown_id_returns_404(client):
    assert_error(client.patch(f"{BASE}/{uuid.uuid4()}", json={"quantity": 1}), 404)


def test_patch_duplicate_name_returns_409(client, create_product):
    create_product(name="First")
    second = create_product(name="Second")
    assert_error(client.patch(f"{BASE}/{second['id']}", json={"name": "FIRST"}), 409)




def test_delete_returns_204_then_404(client, create_product):
    created = create_product()

    response = client.delete(f"{BASE}/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""

    assert_error(client.get(f"{BASE}/{created['id']}"), 404)


def test_delete_unknown_id_returns_404(client):
    assert_error(client.delete(f"{BASE}/{uuid.uuid4()}"), 404)


def test_delete_malformed_id_returns_400(client):
    assert_error(client.delete(f"{BASE}/123"), 400)



def test_unsupported_method_returns_405(client):
    response = client.delete(BASE)
    assert_error(response, 405)
    assert "Allow" in response.headers


def test_unknown_route_returns_404_in_standard_format(client):
    assert_error(client.get("/api/v1/nothing-here"), 404, "Resource not found")


def test_unexpected_error_returns_500_without_internals(app):
    class Broken:
        def get(self, _):
            raise RuntimeError("database password is hunter2")

    app.dependency_overrides[get_product_service] = lambda: Broken()
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.get(f"{BASE}/{uuid.uuid4()}")

    body = assert_error(response, 500)
    assert "hunter2" not in response.text
    assert "Traceback" not in response.text
    assert body["details"] == []


def test_request_id_is_echoed(client):
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"
