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

## API Routes and How to Call Them
Base URL defaults to `http://localhost:8000`. All payloads are JSON; send `Content-Type: application/json`.

### Books
- `GET /books` — List books with filters. Query: `q` (full-text + trigram search), `title`, `isbn`, `author_id`, `before`/`after` (year), `limit` (1–100, default 20), `offset` (works only when `cursor` is absent), `cursor` (keyset pagination only when primary sort is similarity), `sort` (repeatable; `title:asc`, `year:desc`, `similarity:desc`; `similarity` requires `q`). Response: `{"items": [...], "next_cursor": "..."|null}` with authors embedded on each item. Example: `curl 'http://localhost:8000/books?q=asimov&sort=similarity:desc&limit=5'`.
- `GET /books/{book_id}` — Book detail (authors + reviews). 404 if missing.
- `GET /books/{book_id}/reviews` — All reviews for a book.
- `POST /books` — Create book. Body `{"title": "...", "year": 1999, "book_isbn": "...", "genre_name": "...", "description": "...", "author_ids": [1,2]}`. Author IDs must exist; returns created book with authors.
- `POST /books/{book_id}/reviews` — Add review. Body `{"reviewer_name": "...", "rating": 1-5, "comment": "..."}`. Fails with 400 if the reviewer already reviewed the book.
- `PUT /books/{book_id}` — Replace a book using the same shape as `POST /books` (authors overwritten).
- `PUT /books/{book_id}/authors` — Replace the book’s author list. Body is an array of author IDs, e.g., `[3,4]`.
- `PATCH /books/{book_id}` — Partial update. Any subset of `title`, `year`, `book_isbn`, `genre_name`, `description`.
- `DELETE /books/{book_id}` — Delete book and cascade-delete its reviews. 204 on success.

### Authors
- `GET /authors` — List authors. Query: `q` (unaccented similarity on name/email), `name`, `email`, `limit` (1–100, default 20), `offset` (default 0). Returns `[{id, name, email}]`.
- `GET /authors/{author_id}` — Single author. Returns `{id, name, email}`; 404 if missing.
- `GET /authors/{author_id}/books` — Books for an author. Returns `[{id, title, year}]`.
- `POST /authors` — Create author. Body `{"name": "...", "email": "...", "book_ids": [1,2]}` (book IDs optional; must exist if provided).
- `PUT /authors/{author_id}` — Replace author with same shape as `POST /authors` (books overwritten).
- `PATCH /authors/{author_id}` — Partial update. `book_ids` is optional; when provided, it replaces the list (empty list clears all).
- `DELETE /authors/{author_id}` — Delete author. 204 on success.

### Reviews
- `DELETE /reviews/{review_id}` — Delete a review by id. 204 on success.
