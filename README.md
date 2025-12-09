# Library Service (FastAPI + Postgres + Redis)

Production-oriented API for managing authors, books, and reviews. Uses FastAPI with SQLAlchemy (sync), PostgreSQL for storage, and Redis for caching list/detail reads with cache-version invalidation.

## Stack and Capabilities
- FastAPI, Uvicorn, Pydantic v2.
- SQLAlchemy 2.x (sync) with PostgreSQL; migrations via Alembic.
- Redis caching (per-entity entries + versioned list caches).
- Author/book/review CRUD, full-text-ish search with similarity filters, cursor/offset pagination for books.

## Running the API
### Docker Compose (recommended)
1) Set environment (either `.env` or export):
```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=123456
POSTGRES_DB=library_app
DB_HOST=db
DB_PORT=5432
REDIS_HOST=redis
APP_PORT=8000
```
2) Build and start: `docker-compose up --build`
3) Apply migrations (inside the app container): `alembic upgrade head`
4) API available at `http://localhost:8000` (docs at `/docs`).

### Local (without containers)
1) Install Python 3.11+ and dependencies: `pip install -r requirements.txt`
2) Provide `DATABASE_URL` (e.g., `postgresql+psycopg://postgres:123456@localhost:5432/library_app`) and `REDIS_HOST`/`REDIS_PORT` via env or `.env`.
3) Run migrations: `alembic upgrade head`
4) Start the server: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`

## Caching Notes
- Keys: `author:{id}`, `book:{id}`, list keys with versioning (`authors:list`, `books:list`).
- TTL defaults to 300s. Mutations bump list versions and invalidate related detail/review caches.
- Redis URL is built from `REDIS_*` envs; override with `REDIS_URL` if needed.

## Data and Seeding
- Generate sample payload: `python scripts/generate_big_data.py` (default synthetic 50k books to `data_feeding.txt`; toggle `FETCH_FROM_OPEN_LIBRARY` for live samples).
- Seed the running API from that file: `python scripts/seed.py` (assumes API at `http://localhost:8000`).

## Development Tips
- Migrations live in `migrations/`; use `alembic revision --autogenerate -m "msg"` then `alembic upgrade head`.
- SQLAlchemy sessions are synchronous; plan for async migration by switching to `AsyncSession` and async drivers, and ensuring background workers (Celery/RQ/Arq) reuse Redis for cache invalidation if introduced.
- Keep `pydantic` instantiation via `model_validate(..., from_attributes=True)` for ORM objects (already applied).

## Roadmap / Next Steps
- Move to async stack (async SQLAlchemy + async Redis client).
- Introduce background worker for heavy tasks (e.g., bulk imports, cache warming).
- Add auth/rate limiting and request logging/metrics for production.
- Expand tests around caching invariants and search/pagination edge cases.
