# Library App (FastAPI)

Small FastAPI project for managing authors, books, and reviews with PostgreSQL + SQLAlchemy.

## Quickstart
- Python 3.11+ recommended. Install deps: `pip install fastapi uvicorn sqlalchemy psycopg[binary]`.
- Configure database URL (Postgres) via env var, or edit `database.py`:
  - Default: `postgresql+psycopg://postgre:123456@localhost:5432/library-app`
  - Ensure the user/password/database exist, or override with your own credentials.
- Initialize tables: `python -c "import main"` (or let FastAPI import create them on first run).
- Run the API: `uvicorn main:app --reload`.
- Docs: open http://127.0.0.1:8000/docs.

## Data Model
- Author ⇄ Book: many-to-many (`author_book_relation`).
- Book → Review: one-to-many (reviews cascade-delete with books).
- Constraints: book.year must be > 0 if set; review.rating must be 1–5.

## API
Authors (`/authors`)
- POST `/authors` — create (body: name, email?, book_ids?).
- GET `/authors` — list authors (with their books).
- GET `/authors/{author_id}` — get one (with books).
- PUT `/authors/{author_id}` — replace name/email and linked books.
- PATCH `/authors/{author_id}` — partial update (name/email, optional book_ids).
- DELETE `/authors/{author_id}` — delete author (books remain, author removed from them).

Books (`/books`)
- POST `/books` — create (title, year?, author_ids?; validates authors exist).
- GET `/books?author_id=` — list books, optionally filtered by author_id; returns nested authors and reviews.
- GET `/books/{book_id}` — get one book with nested authors and reviews.
- PUT `/books/{book_id}` — replace title/year and author list.
- PATCH `/books/{book_id}` — partial update of title/year (authors untouched).
- PUT `/books/{book_id}/authors` — replace the book’s authors with a new list of author_ids (validated).

Reviews (`/books/{book_id}/reviews`, `/reviews`)
- POST `/books/{book_id}/reviews` — add review to a book (reviewer_name, rating 1–5, comment?).
- GET `/books/{book_id}/reviews` — list reviews for a book.
- DELETE `/reviews/{review_id}` — delete a review.

## Schemas (selected)
- `BookRead`: id, title, year, authors[], reviews[] (reviews only include rating, comment in nested view).
- `ReviewCreate/Update`: rating validated to 1–5.

## Notes
- On Postgres connection errors, verify the credentials/DB in `database.py` or set `DATABASEURL` accordingly.
- Relationships eager-load via `selectinload` to avoid N+1 issues in list/detail endpoints.
