import os
import uuid

import httpx
import pytest
import pytest_asyncio

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")


@pytest_asyncio.fixture
async def client():
    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=15.0, follow_redirects=True
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_create_and_fetch_book_with_author(client):
    # Skip cleanly if the API is not running.
    try:
        health = await client.get("/authors", params={"limit": 1, "offset": 0})
    except httpx.TransportError as exc:
        pytest.skip(f"API not reachable at {BASE_URL}: {exc}")
    if health.status_code >= 500:
        pytest.skip(f"API unhealthy at {BASE_URL}: status {health.status_code}")

    suffix = uuid.uuid4().hex[:8]
    author_payload = {
        "name": f"Test Author {suffix}",
        "email": f"{suffix}@example.com",
        "book_ids": [],
    }
    book_id = None

    # Create author
    resp = await client.post("/authors/", json=author_payload)
    assert resp.status_code == 200, f"create author failed: {resp.text}"
    author = resp.json()
    author_id = author["id"]

    # Create book linked to that author
    isbn = f"978{uuid.uuid4().int % 10**10:010d}"
    book_payload = {
        "title": f"Async Test Book {suffix}",
        "year": 2024,
        "book_isbn": isbn,
        "genre_name": "test",
        "description": "async integration test payload",
        "author_ids": [author_id],
    }
    resp = await client.post("/books/", json=book_payload)
    assert resp.status_code == 200, f"create book failed: {resp.text}"
    book = resp.json()
    book_id = book["id"]

    # Fetch book detail and assert author is present
    resp = await client.get(f"/books/{book_id}")
    assert resp.status_code == 200, f"get book failed: {resp.text}"
    detail = resp.json()
    assert detail["title"] == book_payload["title"]
    assert any(a["id"] == author_id for a in detail["authors"])

    # Cleanup to keep tests idempotent
    await client.delete(f"/books/{book_id}")
    await client.delete(f"/authors/{author_id}")
