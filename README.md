Product Management API

A backend application developed using **Python, FastAPI, PostgreSQL, and SQLAlchemy** to manage product information through RESTful APIs.

The application provides a structured approach to product management, including product creation, retrieval, modification, deletion, data validation, filtering, sorting, and pagination.

It follows a layered architecture to keep business logic, API handling, and database operations separate and maintainable.

---

#1. Introduction

The Product Management API is designed to provide a centralized service for handling product-related information in an online commerce system.

It exposes REST endpoints that allow clients and other services to interact with product records.

Main Capabilities

- Add new products to the system.
- View individual product information.
- Retrieve product collections.
- Modify existing product records.
- Update selected product attributes.
- Remove products from the database.
- Search products using different criteria.
- Navigate large datasets through pagination.
- Arrange product results using sorting options.
- Validate incoming data before processing.
- Handle application errors through a centralized mechanism.

---

 2. Tools and Technologies

| Technology | Implementation |
|---|---|
| Python 3.14 | Backend development |
| FastAPI | API development |
| PostgreSQL | Relational database |
| SQLAlchemy | Database interaction |
| Pydantic | Data validation |
| Alembic | Database version management |
| Uvicorn | Application server |
| Pytest | Automated testing |
| HTTPX | API testing |
| Pytest-Cov | Test coverage analysis |

---

 3. Application Design

The project uses a layered backend design. Each component is responsible for a particular part of the request-processing workflow.

### Request Processing Flow

Client → Controller → Service → Repository → Database

Components

**1. Controller**

- Exposes API routes.
- Accepts client requests.
- Processes request parameters.
- Returns appropriate HTTP responses.

**2. Service**

- Contains the application's business rules.
- Coordinates product-related operations.
- Checks for duplicate product names.
- Handles business-level exceptions.

**3. Repository**

- Communicates with the database.
- Executes product-related queries.
- Implements data retrieval and modification.
- Supports filtering, ordering, and pagination.

**4. Database**

- Stores product information permanently.
- Maintains data relationships and constraints.
- Uses SQLAlchemy for database communication.
- Uses Alembic to manage schema changes.

---

## 4. Directory Organization

```text
Product_Service/
│
├── app/
│   ├── controllers/
│   │   └── product_controller.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logging_config.py
│   │
│   ├── db/
│   │   └── session.py
│   │
│   ├── models/
│   │   └── product.py
│   │
│   ├── repositories/
│   │   └── product_repository.py
│   │
│   ├── schemas/
│   │   ├── error.py
│   │   └── product.py
│   │
│   ├── services/
│   │   └── product_service.py
│   │
│   └── main.py
│
├── alembic/
│   └── versions/
│
├── tests/
│   ├── unit/
│   │   └── test_product_service.py
│   │
│   └── integration/
│       ├── conftest.py
│       └── test_product_api.py
│
├── logs/
├── .env
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## 5. Database Setup

The application uses PostgreSQL to store and manage product records.

**Database configuration:**

- Primary database: `product_service`
- Testing database: `product_service_test`

Create a `.env` file in the root directory:

```env
APP_NAME=Product Management API
APP_ENV=development
DEBUG=True

DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/product_service

TEST_DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/product_service_test

API_V1_PREFIX=/api/v1
```

Replace `YOUR_PASSWORD` with your PostgreSQL password.

Keep the `.env` file out of version control to protect database credentials.

---

## 6. Product Data Structure

Product records are maintained in the `products` table.

| Attribute | Purpose |
|---|---|
| id | Unique identifier for each product |
| name | Product name |
| description | Additional product information |
| price | Selling price |
| quantity | Available stock |
| category | Product classification |
| status | Current product state |
| created_at | Record creation date and time |
| updated_at | Most recent modification date and time |

### Data Integrity
