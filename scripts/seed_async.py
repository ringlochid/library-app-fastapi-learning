"""
Async seeding script to populate the running API with authors and books.

Usage:
    python scripts/seed_async.py --authors 20 --books 50 --base-url http://localhost:8000

The API must be running and reachable at the provided base URL.
"""

import argparse
import asyncio
import os
import random
import uuid

import httpx

DEFAULT_BASE_URL = os.getenv("SEED_BASE_URL", "http://localhost:8000")


def _isbn() -> str:
    # Generate a 13-digit ISBN-like string
    return f"978{uuid.uuid4().int % 10**10:010d}"


async def create_author(client: httpx.AsyncClient, name: str, email: str) -> int:
    resp = await client.post(
        "/authors/",
        json={"name": name, "email": email, "book_ids": []},
    )
    resp.raise_for_status()
    return resp.json()["id"]


async def create_book(
    client: httpx.AsyncClient, title: str, author_ids: list[int], description: str
) -> int:
    payload = {
        "title": title,
        "year": 2024,
        "book_isbn": _isbn(),
        "genre_name": "seed",
        "description": description,
        "author_ids": author_ids,
    }
    resp = await client.post("/books/", json=payload)
    resp.raise_for_status()
    return resp.json()["id"]


async def seed(
    base_url: str, authors: int, books: int, min_authors_per_book: int, max_authors_per_book: int
):
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        author_ids: list[int] = []
        for idx in range(authors):
            suffix = uuid.uuid4().hex[:6]
            author_id = await create_author(
                client,
                name=f"Seed Author {idx}-{suffix}",
                email=f"seed-{suffix}@example.com",
            )
            author_ids.append(author_id)

        if not author_ids:
            print("No authors created; skipping book creation.")
            return

        created_books: list[int] = []
        for idx in range(books):
            suffix = uuid.uuid4().hex[:6]
            upper = min(max_authors_per_book, len(author_ids))
            lower = min(min_authors_per_book, upper)
            sample_size = random.randint(lower, upper)
            selected_authors = random.sample(author_ids, k=sample_size)
            book_id = await create_book(
                client,
                title=f"Seed Book {idx}-{suffix}",
                author_ids=selected_authors,
                description="seeded via scripts/seed_async.py",
            )
            created_books.append(book_id)

    print(
        f"Seeded {len(author_ids)} authors and {len(created_books)} books to {base_url}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Async seeder for the Library API")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--authors", type=int, default=10, help="Number of authors to create")
    parser.add_argument("--books", type=int, default=20, help="Number of books to create")
    parser.add_argument(
        "--min-authors-per-book",
        type=int,
        default=1,
        help="Minimum authors to attach to a book",
    )
    parser.add_argument(
        "--max-authors-per-book",
        type=int,
        default=2,
        help="Maximum authors to attach to a book",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    asyncio.run(
        seed(
            base_url=args.base_url,
            authors=args.authors,
            books=args.books,
            min_authors_per_book=args.min_authors_per_book,
            max_authors_per_book=args.max_authors_per_book,
        )
    )


if __name__ == "__main__":
    main()
