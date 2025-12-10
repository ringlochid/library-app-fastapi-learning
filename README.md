# Library Service (FastAPI + Postgres + Redis)

Production-oriented API for managing authors, books, and reviews. Uses FastAPI with SQLAlchemy (async), PostgreSQL for storage, and Redis for caching list/detail reads with cache-version invalidation. Deployed and exercised against App Runner + RDS + ElastiCache (TLS).

## Stack and Capabilities
- FastAPI + Uvicorn, Pydantic v2.
- SQLAlchemy 2.x (async) with PostgreSQL (RDS in production); migrations via Alembic.
- Redis caching (ElastiCache Redis, TLS, cluster-safe deletes to avoid CROSSSLOT), per-entity + versioned list caches.
- Containerized image deployed via AWS App Runner with VPC connector to RDS/Redis.
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

### App Runner + RDS + ElastiCache (deployed)
- Image: `681802564174.dkr.ecr.ap-southeast-2.amazonaws.com/library-app:latest`
- DB: RDS Postgres, `DATABASE_SYNC_URL` / `DATABASE_ASYNC_URL` point to RDS.
- Redis: ElastiCache Redis (TLS required) with `REDIS_URL=rediss://<endpoint>:6379/0`.
- Start command can use Dockerfile CMD, or `sh -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"` if you want migrations on startup.

## Caching Notes
- Keys: `author:{id}`, `book:{id}`, list keys with versioning (`authors:list`, `books:list`).
- TTL defaults to 300s. Mutations bump list versions and invalidate related detail/review caches.
- Redis URL is built from `REDIS_*` envs; override with `REDIS_URL` if needed. For Redis cluster/TLS, use `rediss://…` and single-key deletes are used to avoid CROSSSLOT errors.

## Data and Seeding
- Generate sample payload: `python scripts/generate_big_data.py` (default synthetic 50k books to `data_feeding.txt`; toggle `FETCH_FROM_OPEN_LIBRARY` for live samples).
- Seed (async) from file: `python scripts/seed_file_async.py --base-url https://<your-app> --data-file data_feeding.txt --concurrency 10` (uses `.env` / `SEED_BASE_URL` if set).
- Legacy sync seed: `python scripts/seed.py` (assumes `http://localhost:8000`).

## Development Tips
- Migrations live in `migrations/`; use `alembic revision --autogenerate -m "msg"` then `alembic upgrade head`.
- SQLAlchemy is async in the API layer; ensure any new background workers reuse the async engine/session and Redis client.
- Keep `pydantic` instantiation via `model_validate(..., from_attributes=True)` for ORM objects (already applied).

## Roadmap / Next Steps
- Add auth and rate limiting; protect public endpoint (WAF/API key/JWT).
- Add request logging/metrics and basic observability.
- Media pipeline to S3 (covers, PDFs, avatars) with presigned URLs.
- Add a worker for bulk imports/cache warming.
- Expand tests around caching invariants, search/pagination edge cases, and high-concurrency writes.

## Deployed / Tested
- App Runner + RDS + ElastiCache (TLS) seeded successfully via `scripts/seed_file_async.py` with 116 authors and 50,000 books.

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
