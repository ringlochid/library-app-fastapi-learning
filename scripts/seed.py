import json, requests

BASE = "http://localhost:8000"

with open("data_feeding.txt") as f:
    data = json.load(f)

idx_to_id = {}
for idx, author in enumerate(data["authors"], start=1):
    r = requests.post(f"{BASE}/authors/", json={
        "name": author["name"],
        "email": author["email"],
        "book_ids": []
    })
    r.raise_for_status()
    idx_to_id[idx] = r.json()["id"]

for book in data["books"]:
    payload = {
        "title": book["title"],
        "year": book["year"],
        "book_isbn": book["book_isbn"],
        "genre_name": book["genre_name"],
        "description": book["description"],
        "author_ids": [idx_to_id[i] for i in book.get("author_ids", [])],
    }
    r = requests.post(f"{BASE}/books/", json=payload)
    r.raise_for_status()
    print(f"Created book {r.json()['id']}: {book['title']}")