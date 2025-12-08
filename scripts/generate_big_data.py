import json
from pathlib import Path
from typing import Iterable

import requests


# List of popular authors to pull from Open Library.
SEED_AUTHORS: list[str] = [
    "Harper Lee",
    "George Orwell",
    "F. Scott Fitzgerald",
    "Jane Austen",
    "J.R.R. Tolkien",
    "J.K. Rowling",
    "Leo Tolstoy",
    "Mark Twain",
    "Mary Shelley",
    "Fyodor Dostoevsky",
    "Gabriel Garcia Marquez",
    "Franz Kafka",
    "Ernest Hemingway",
    "Virginia Woolf",
    "Agatha Christie",
    "C.S. Lewis",
    "Arthur Conan Doyle",
    "Isaac Asimov",
    "Philip K. Dick",
    "Ursula K. Le Guin",
    "Neil Gaiman",
    "Margaret Atwood",
    "Kazuo Ishiguro",
    "Brandon Sanderson",
    "N.K. Jemisin",
    "Stephen King",
    "Dan Brown",
    "James Patterson",
    "John Grisham",
    "Paulo Coelho",
    "Khaled Hosseini",
    "Suzanne Collins",
    "Veronica Roth",
    "Rick Riordan",
    "Nicholas Sparks",
    "Michael Crichton",
    "Arthur C. Clarke",
    "H. G. Wells",
    "Aldous Huxley",
    "Ray Bradbury",
    "Douglas Adams",
    "J.D. Salinger",
    "Haruki Murakami",
    "Kurt Vonnegut",
    "Terry Pratchett",
    "Roald Dahl",
    "Jules Verne",
    "Alexandre Dumas",
    "Victor Hugo",
    "Charles Dickens",
    "Jack London",
    "Homer",
    "Herman Melville",
    "William Shakespeare",
    "Dante Alighieri",
    "H.P. Lovecraft",
    "Edgar Allan Poe",
    "Robert Louis Stevenson",
    "Ayn Rand",
    "Ian Fleming",
    "Stieg Larsson",
    "Gillian Flynn",
    "Patricia Highsmith",
    "Lee Child",
    "Michael Connelly",
    "Donna Tartt",
    "Elena Ferrante",
    "Sally Rooney",
    "Colleen Hoover",
    "Madeline Miller",
    "Anthony Doerr",
    "Celeste Ng",
    "Chimamanda Ngozi Adichie",
    "Margaret Mitchell",
    "Louisa May Alcott",
    "Emily Bronte",
    "Charlotte Bronte",
    "Bram Stoker",
    "Oscar Wilde",
    "George R.R. Martin",
    "Tana French",
    "Jo Nesbo",
    "Ken Follett",
    "Daphne du Maurier",
    "Anne Rice",
    "Diana Gabaldon",
    "Patrick Rothfuss",
    "Robert Jordan",
    "Andrzej Sapkowski",
    "Brent Weeks",
    "Robin Hobb",
    "Stephenie Meyer",
    "Christopher Paolini",
    "Erin Morgenstern",
    "Ransom Riggs",
    "Lois Lowry",
    "Madeleine L'Engle",
    "Lemony Snicket",
    "Eoin Colfer",
    "David Baldacci",
    "Tom Clancy",
    "Clive Cussler",
    "Vince Flynn",
    "Orson Scott Card",
    "Lois McMaster Bujold",
    "Terry Brooks",
    "Rick Yancey",
    "Cassandra Clare",
    "Leigh Bardugo",
    "Pierce Brown",
    "Marie Lu",
    "Sabaa Tahir",
    "Naomi Novik",
    "Nora Roberts",
    "Deborah Harkness",
    "Charlaine Harris",
]

TARGET_BOOKS = 11000  # stop once we have this many books
OUTPUT_PATH = Path("data_feeding.txt")
MAX_TITLE_LEN = 200


def slug_email(name: str) -> str:
    slug = (
        name.lower()
        .replace(" ", ".")
        .replace("'", "")
        .replace(",", "")
        .replace(".", ".")
    )
    return f"{slug}@example.com"


def fetch_docs(author: str, per_author_limit: int = 40) -> Iterable[dict]:
    """Fetch book docs for one author from Open Library."""
    try:
        resp = requests.get(
            "https://openlibrary.org/search.json",
            params={
                "author": author,
                "language": "eng",
                "limit": per_author_limit,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("docs", [])
    except Exception as exc:  # pragma: no cover - for dev convenience
        print(f"Skipping {author}: {exc}")
        return []

def clip_title(title: str) -> str:
    """Ensure title fits DB column length."""
    return title[:MAX_TITLE_LEN]


def main() -> None:
    authors = [
        {"name": name, "email": slug_email(name), "book_ids": []}
        for name in SEED_AUTHORS
    ]
    author_lookup = {a["name"].lower(): idx + 1 for idx, a in enumerate(authors)}

    books: list[dict] = []
    seen: set[tuple[str, tuple[int, ...]]] = set()

    for name in SEED_AUTHORS:
        docs = fetch_docs(name)
        primary_author_id = author_lookup.get(name.lower())

        for doc in docs:
            if len(books) >= TARGET_BOOKS:
                break
            title_raw = doc.get("title")
            if not title_raw:
                continue

            title = clip_title(title_raw)
            if not title:
                continue

            isbn_list = doc.get("isbn") or []
            book_isbn = next((i for i in isbn_list if len(i) in (10, 13)), None)
            year_raw = doc.get("first_publish_year")
            year = year_raw if isinstance(year_raw, int) and year_raw > 0 else None

            subjects = doc.get("subject") or []
            genre = subjects[0] if subjects else "General"
            description = (
                "; ".join(subjects[:3])
                if subjects
                else f"A popular book by {name}."
            )

            author_names = [a for a in (doc.get("author_name") or []) if a]
            author_ids = [
                author_lookup[a.lower()]
                for a in author_names
                if a.lower() in author_lookup
            ]
            if not author_ids and primary_author_id:
                author_ids = [primary_author_id]
            if not author_ids:
                continue

            key = (title.lower(), tuple(sorted(author_ids)))
            if key in seen:
                continue

            seen.add(key)
            books.append(
                {
                    "title": title,
                    "year": year,
                    "book_isbn": book_isbn,
                    "genre_name": genre,
                    "description": description,
                    "author_ids": author_ids,
                }
            )

    # if we still need more, synthesize filler titles so we always have 1000+
    while len(books) < TARGET_BOOKS:
        idx = len(books) + 1
        author_id = (idx % len(authors)) + 1
        books.append(
            {
                "title": f"Collected Stories Volume {idx}",
                "year": 2000 + (idx % 24),
                "book_isbn": f"999{idx:010d}",  # 13 digits to satisfy ISBN constraint
                "genre_name": "Popular Fiction",
                "description": "Auto-generated filler from the top authors list.",
                "author_ids": [author_id],
            }
        )

    payload = {"authors": authors, "books": books}
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(authors)} authors and {len(books)} books to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
