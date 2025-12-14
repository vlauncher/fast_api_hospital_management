# Hospital Management System Backend - Project Overview

This document provides a concise overview of the Hospital Management System (HMS) backend, built with FastAPI, for instructional context and efficient future interactions.

## Project Overview

The project is a **production-grade Hospital Management System (HMS)** backend designed to manage real-world healthcare workflows with a focus on enterprise-level security, scalability, and compliance. It is engineered to support a 500-bed hospital, 200+ concurrent users, and 5000+ daily transactions.

**Key Features:**
*   Authentication & Authorization (JWT, RBAC, ABAC)
*   Patient Management (with PII encryption)
*   Electronic Medical Records (EMR)
*   Appointment & Scheduling
*   Pharmacy Management
*   Laboratory Management (LIMS)
*   Billing & Invoicing
*   Inpatient Management
*   Audit Logging and Reporting

**Main Technologies:**
*   **Backend Framework:** FastAPI (Python 3.11+)
*   **Database:** PostgreSQL 15+ (async via SQLAlchemy 2.0+ and asyncpg)
*   **ORM:** SQLAlchemy 2.0+
*   **Migrations:** Alembic
*   **Caching/Messaging:** Redis 7+, RabbitMQ (implicitly via Celery)
*   **Background Tasks:** Celery 5.3+
*   **Configuration:** Pydantic-settings
*   **Containerization:** Docker, Docker Compose
*   **Testing:** Pytest

**Architecture:**
The system follows a **Modular Monolith with Event-Driven Architecture**, adhering to:
*   **Domain-Driven Design (DDD):** Each module represents a bounded context.
*   **SOLID Principles:** For maintainable, testable code.
*   **Event Sourcing:** Critical operations emit events for audit trails.
*   **CQRS Pattern:** Separate read and write models for complex queries.
*   **API-First Design:** OpenAPI 3.0 specification-driven development.

## Building and Running

### Prerequisites
*   Docker and Docker Compose
*   Python 3.11+
*   Poetry (or pip for `requirements.txt`)

### 1. Environment Setup

Copy the example environment file and populate it with your settings.
```bash
cp .env.example .env
# Edit .env to configure DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY, etc.
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
# Or if using poetry
# poetry install
```

### 3. Database Migrations (using Alembic)
First, ensure your database (PostgreSQL) is running and accessible as configured in `.env`.
```bash
alembic upgrade head
```

### 4. Running with Docker Compose (Recommended for Development)

This will set up the FastAPI application, PostgreSQL, Redis, and RabbitMQ.
```bash
docker-compose up --build
```
The API will be available at `http://localhost:8000`.

### 5. Running Locally (without Docker for services)

Ensure PostgreSQL, Redis, and RabbitMQ are running and accessible.
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
```

### 6. Running Celery Worker

The Celery worker processes background tasks. It should be run in a separate terminal.
```bash
celery -A app.workers.celery_app worker --loglevel=info
```
For local development, it's configured to run without explicit worker setup if `APP_ENV` is "development" as seen in `app/main.py`.

## Testing

The project uses `pytest` for testing.

### Running Tests
```bash
pytest
```

### Running Tests with Coverage Report
```bash
pytest --cov=app --cov-report=term-missing --cov-report=html:htmlcov
```

### Specific Test Types (using markers)
*   **Unit Tests:** `pytest -m unit`
*   **Integration Tests:** `pytest -m integration`
*   **Authentication Tests:** `pytest -m auth`

## Development Conventions

*   **Python Version:** 3.11+
*   **FastAPI Version:** 0.109+
*   **SQLAlchemy Version:** 2.0+ (async)
*   **Code Structure:** Follows a modular monolith pattern with clear separation of `api/`, `domain/`, `infrastructure/`, and `workers/`.
*   **Configuration:** Managed via `app/core/config.py` using `pydantic-settings`, loading from `.env` files.
*   **Authentication:** JWT-based (Access and Refresh tokens) with HS256 algorithm.
*   **Authorization:** Multi-layered approach:
    *   **Role-Based Access Control (RBAC):** Coarse-grained permissions assigned to roles.
    *   **Resource-Based Authorization:** Fine-grained checks on specific resources.
    *   **Attribute-Based Access Control (ABAC):** Context-aware permissions based on attributes.
    *   **Permission Format:** `resource:action[:scope]` (e.g., `patients:read:department`, `emr:write`).
*   **Database:** PostgreSQL with Alembic for migrations, SQLAlchemy ORM for interactions.
*   **Asynchronous Operations:** Heavily utilizes `async`/`await` for I/O bound operations.
*   **Logging:** Structured logging configured in `app/main.py`.
*   **Error Handling:** Global exception handlers for consistent API responses.
*   **Security:** CORS, TrustedHost, X-Process-Time, X-Request-ID, Rate Limiting, Security Headers middleware implemented.

This `GEMINI.md` provides a quick reference for understanding, developing, and extending the Hospital Management System.
