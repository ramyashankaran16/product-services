# Product Service

A REST service that manages products for an online store (Microservices Track, Task 1).
Built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2** and **Alembic**, in a layered
structure: controller → service → repository.

## Prerequisites

- Python 3.11 or newer
- PostgreSQL 14+ (or Docker, to run it with `docker compose`)
- Git

## Quick start (about 5 minutes)

```bash
# 1. Get the code and create a virtual environment
git clone <your-repo-url> product-service
cd product-service
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# 2. Configure
cp .env.example .env               # Windows: copy .env.example .env
# edit .env and set your own password in DATABASE_URL and POSTGRES_PASSWORD

# 3. Start PostgreSQL (skip if you already have one running)
docker compose up -d db

# 4. Create the schema
alembic upgrade head

# 5. Run the service
python -m app                       # or: uvicorn app.main:app --reload
```

Open http://localhost:8000/health → `{"status":"UP","database":"UP"}`
Interactive API docs: http://localhost:8000/docs (Swagger UI). The OpenAPI file is also saved in `docs/openapi.json`.

### Using an existing PostgreSQL instead of Docker

```sql
CREATE USER product_user WITH PASSWORD 'your-password';
CREATE DATABASE products OWNER product_user;
```
Then put the matching URL in `.env`.

## Configuration

All settings come from environment variables (or `.env`). Nothing is hard-coded.

| Variable       | Required | Default    | Description |
|----------------|----------|------------|-------------|
| `DATABASE_URL` | yes      | —          | e.g. `postgresql+psycopg://user:pass@localhost:5432/products` |
| `APP_HOST`     | no       | `0.0.0.0`  | Bind address |
| `APP_PORT`     | no       | `8000`     | HTTP port |
| `LOG_LEVEL`    | no       | `INFO`     | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ENVIRONMENT`  | no       | `local`    | Free-text environment name |

## Running the tests

```bash
pytest
```

One command runs unit tests, API tests and a migration test against an in-memory SQLite
database (built by the real Alembic migrations), and prints coverage. The run fails if
coverage drops below 70%. No PostgreSQL is needed for tests.

## API overview

Base path: `/api/v1/products`

| Method | Path                      | Purpose                     | Success |
|--------|---------------------------|-----------------------------|---------|
| POST   | `/api/v1/products`        | Create a product            | 201 + `Location` |
| GET    | `/api/v1/products/{id}`   | Get one product             | 200 |
| GET    | `/api/v1/products`        | List (page, filter, sort)   | 200 |
| PUT    | `/api/v1/products/{id}`   | Replace a product           | 200 |
| PATCH  | `/api/v1/products/{id}`   | Partially update a product  | 200 |
| DELETE | `/api/v1/products/{id}`   | Delete a product (hard)     | 204 |
| GET    | `/health`                 | Health check (incl. DB)     | 200 (503 if DB down) |

### List parameters

- `page` — **starts at 1**, default 1
- `size` — default 10, maximum 100 (larger values are rejected with 400)
- `category` — exact match, case-insensitive
- `status` — `ACTIVE` or `INACTIVE`
- `minPrice`, `maxPrice` — inclusive; `minPrice` must be ≤ `maxPrice`
- `sort` — `<field>,<asc|desc>`; fields: `name`, `price`, `quantity`, `category`, `createdAt`, `updatedAt`.
  Default `createdAt,desc`. Direction defaults to `asc` if omitted.

### Example requests

```bash
# Create
curl -i -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Wireless Mouse","price":19.99,"quantity":50,"category":"Electronics"}'

# Get
curl http://localhost:8000/api/v1/products/<id>

# List: page 1, 5 per page, electronics between 10 and 100, most expensive first
curl "http://localhost:8000/api/v1/products?page=1&size=5&category=Electronics&minPrice=10&maxPrice=100&sort=price,desc"

# Replace (all required fields must be sent)
curl -X PUT http://localhost:8000/api/v1/products/<id> \
  -H "Content-Type: application/json" \
  -d '{"name":"Wireless Mouse Pro","price":29.99,"quantity":40,"category":"Electronics","status":"ACTIVE"}'

# Partial update
curl -X PATCH http://localhost:8000/api/v1/products/<id> \
  -H "Content-Type: application/json" -d '{"quantity":35}'

# Delete
curl -i -X DELETE http://localhost:8000/api/v1/products/<id>
```

A Postman collection with happy-path and error-case requests is in
`postman/product-service.postman_collection.json` (import it, then run it top to bottom).

### Error format

Every error uses the same shape:

```json
{
  "timestamp": "2026-10-27T10:15:30Z",
  "status": 400,
  "error": "Bad Request",
  "message": "Validation failed",
  "path": "/api/v1/products",
  "details": [{ "field": "price", "issue": "Input should be greater than 0" }]
}
```

| Situation                              | Status |
|----------------------------------------|--------|
| Validation failure, malformed JSON, malformed id, bad query params | 400 |
| Product (or route) not found           | 404 |
| Duplicate product name (case-insensitive) | 409 |
| Unsupported method on a path           | 405 |
| Unexpected server error (details logged, never returned) | 500 |

## Design decisions

- **IDs** are UUIDs generated by the server.
- **Server-managed fields** (`id`, `createdAt`, `updatedAt`) and unknown fields in a request body are **rejected with 400** rather than silently ignored, so client mistakes are visible.
- **Strict types**: `"price": "10"` or `"quantity": 1.5` are type errors; no silent coercion.
- **Whitespace** is trimmed from `name`, `description` and `category` before length checks. An empty description is stored as `null`.
- **PUT** replaces the whole resource: omitted optional fields reset (`description` → null, `status` → ACTIVE).
- **PATCH** changes only the fields sent; `null` is allowed only for `description`; an empty body is a 400.
- **DELETE** is a hard delete. (Soft delete + restore is a listed stretch goal.)
- **Name uniqueness** is checked in the service (clear 409 message) and enforced by a unique index on `lower(name)` in the database (protects against races).
- **Logging**: every request is logged with method, path, status, duration and a correlation id (`X-Request-ID` header, generated if not sent and echoed back). 4xx log at WARNING, 5xx at ERROR with stack trace.

## Project structure

```
app/
  api/             controllers (HTTP only) and dependency wiring
    v1/products.py
    health.py
    dependencies.py
  services/        business rules (no HTTP, no SQL)
  repositories/    database queries
  models/          SQLAlchemy entities (never returned by the API)
  schemas/         request/response DTOs
  exceptions/      domain errors + global handlers
  core/            settings, logging, middleware
  db/              engine and session
  main.py          app factory
alembic/           migrations
tests/             unit/ (service, mocked repo) and integration/ (API + migrations)
docs/              design note, OpenAPI file
postman/           example requests
```

## Known limitations

- Single-field sorting only (one `sort` parameter).
- `category` filter is an exact match, not a partial search.
- No authentication (out of scope for Task 1).
