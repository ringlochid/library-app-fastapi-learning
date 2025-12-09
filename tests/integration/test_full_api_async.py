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
        # quick health check; skip if API unreachable or unhealthy
        try:
            resp = await c.get("/authors", params={"limit": 1, "offset": 0})
            if resp.status_code >= 500:
                pytest.skip(f"API unhealthy at {BASE_URL}: {resp.status_code}")
        except httpx.TransportError as exc:
            pytest.skip(f"API not reachable at {BASE_URL}: {exc}")
        yield c


@pytest.mark.asyncio
async def test_full_crud_flow(client: httpx.AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    author_payload = {
        "name": f"Flow Author {suffix}",
        "email": f"{suffix}@example.com",
        "book_ids": [],
    }

    # Create author
    resp = await client.post("/authors/", json=author_payload)
    assert resp.status_code == 200, f"create author failed: {resp.text}"
    author = resp.json()
    author_id = author["id"]

    # Create book with that author
    isbn = f"978{uuid.uuid4().int % 10**10:010d}"
    book_payload = {
        "title": f"Flow Book {suffix}",
        "year": 2024,
        "book_isbn": isbn,
        "genre_name": "integration",
        "description": "full flow test book",
        "author_ids": [author_id],
    }
    resp = await client.post("/books/", json=book_payload)
    assert resp.status_code == 200, f"create book failed: {resp.text}"
    book = resp.json()
    book_id = book["id"]

    try:
        # List books filtered by author
        resp = await client.get("/books", params={"author_id": author_id, "limit": 5})
        assert resp.status_code == 200, f"list books failed: {resp.text}"
        listed = resp.json()["items"]
        assert any(b["id"] == book_id for b in listed)

        # Patch book (year)
        resp = await client.patch(f"/books/{book_id}", json={"year": 2030})
        assert resp.status_code == 200, f"patch book failed: {resp.text}"
        assert resp.json()["year"] == 2030

        # Add review
        review_payload = {
            "reviewer_name": f"reviewer-{suffix}",
            "rating": 5,
            "comment": "great book",
        }
        resp = await client.post(f"/books/{book_id}/reviews", json=review_payload)
        assert resp.status_code == 200, f"create review failed: {resp.text}"
        review = resp.json()
        review_id = review["id"]

        # Get book detail and ensure review + author present
        resp = await client.get(f"/books/{book_id}")
        assert resp.status_code == 200, f"get book detail failed: {resp.text}"
        detail = resp.json()
        assert any(a["id"] == author_id for a in detail["authors"])
        assert any(r["id"] == review_id for r in detail["reviews"])

        # Delete review
        resp = await client.delete(f"/reviews/{review_id}")
        assert resp.status_code == 204, f"delete review failed: {resp.text}"
    finally:
        # Cleanup to keep subsequent runs clean
        await client.delete(f"/books/{book_id}")
        await client.delete(f"/authors/{author_id}")
