"""
Async seeding script that reads `data_feeding.txt` and populates the running API.

Usage:
    python scripts/seed_file_async.py \
        --base-url https://your-app-runner-url \
        --data-file data_feeding.txt \
        --concurrency 10

The API must be reachable at the given base URL.
"""

import argparse
import asyncio
import json
import os
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv


load_dotenv()

DEFAULT_BASE_URL = os.getenv("SEED_BASE_URL", "http://localhost:8000")
DEFAULT_DATA_FILE = "data_feeding.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Async seeder from data_feeding.txt")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="API base URL (default: %(default)s or SEED_BASE_URL)",
    )
    parser.add_argument(
        "--data-file",
        default=DEFAULT_DATA_FILE,
        help="Path to data JSON file (default: %(default)s)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Max concurrent requests for book creation",
    )
    return parser.parse_args()


async def create_author(client: httpx.AsyncClient, author: Dict[str, Any]) -> int:
    resp = await client.post(
        "/authors/",
        json={
            "name": author["name"],
            "email": author["email"],
            "book_ids": [],
        },
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _normalize_year(year: Any) -> Any:
    if isinstance(year, int) and year <= 0:
        return None
    return year


async def create_book(
    client: httpx.AsyncClient,
    book: Dict[str, Any],
    author_id_map: Dict[int, int],
    semaphore: asyncio.Semaphore,
) -> int:
    async with semaphore:
        mapped_author_ids: List[int] = [
            author_id_map[i]
            for i in book.get("author_ids", [])
            if i in author_id_map
        ]
        payload = {
            "title": book["title"],
            "year": _normalize_year(book.get("year")),
            "book_isbn": book.get("book_isbn"),
            "genre_name": book.get("genre_name"),
            "description": book.get("description"),
            "author_ids": mapped_author_ids,
        }
        resp = await client.post("/books/", json=payload)
        resp.raise_for_status()
        return resp.json()["id"]


async def seed(base_url: str, data_file: str, concurrency: int) -> None:
    with open(data_file, "r") as f:
        data = json.load(f)

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        author_id_map: Dict[int, int] = {}
        for idx, author in enumerate(data.get("authors", []), start=1):
            author_id = await create_author(client, author)
            author_id_map[idx] = author_id
            print(f"Created author {author_id}: {author['name']}")

        if not data.get("books"):
            print("No books in data file; seeding complete.")
            return

        semaphore = asyncio.Semaphore(max(concurrency, 1))
        tasks = []
        for book in data.get("books", []):
            tasks.append(create_book(client, book, author_id_map, semaphore))

        created_books = await asyncio.gather(*tasks)
        print(
            f"Seeded {len(author_id_map)} authors and {len(created_books)} books "
            f"to {base_url} from {data_file}"
        )


def main() -> None:
    args = parse_args()
    asyncio.run(seed(args.base_url, args.data_file, args.concurrency))


if __name__ == "__main__":
    main()
