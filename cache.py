import hashlib
import json
import os
from typing import Any, Iterable

from dotenv import load_dotenv
from redis import Redis, from_url

load_dotenv()

_redis: Redis | None = None
DEFAULT_TTL = 300
VERSION_KEY_PREFIX = "cache:version:"


def get_cache_version(name: str, r: Redis | None = None) -> int:
    r = r or get_redis()
    raw = r.get(f"{VERSION_KEY_PREFIX}{name}")
    return int(raw) if raw is not None else 1


def bump_cache_version(name: str, r: Redis | None = None) -> int:
    r = r or get_redis()
    return int(r.incr(f"{VERSION_KEY_PREFIX}{name}"))


def _build_redis_url() -> str:
    if raw := os.getenv("REDIS_URL"):
        return raw

    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    db = os.getenv("REDIS_DB", "0")
    return f"redis://{host}:{port}/{db}"


REDIS_URL = _build_redis_url()


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = from_url(
            REDIS_URL,
            decode_responses=True,
        )
    return _redis


def normalize_params(params: dict) -> tuple[dict, str]:
    clean = {k: v for k, v in params.items() if v is not None}
    payload = json.dumps(clean, sort_keys=True, separators=(",", ":"))
    return clean, payload


def make_list_key(prefix: str, params: dict, version: int = 1) -> str:
    _, payload = normalize_params(params)
    h = hashlib.sha1(payload.encode()).hexdigest()[:16]  # trim to 16
    return f"{prefix}:v{version}:{h}"


def make_list_key_with_payload(
    prefix: str, params: dict, version: int = 1
) -> tuple[str, str]:
    clean, payload = normalize_params(params)
    h = hashlib.sha1(payload.encode()).hexdigest()[:16]
    return f"{prefix}:v{version}:{h}", payload


def make_books_list_key(
    params: dict, version: int | None = None, r: Redis | None = None
):
    if version is None:
        version = get_cache_version("books:list", r)
    return make_list_key_with_payload("books:list", params, version)


def make_authors_list_key(
    params: dict, version: int | None = None, r: Redis | None = None
) -> tuple[str, str]:
    if version is None:
        version = get_cache_version("authors:list", r)
    return make_list_key_with_payload("authors:list", params, version)


def make_book_key(book_id: int) -> str:
    return f"book:{book_id}"


def make_author_key(author_id: int) -> str:
    return f"author:{author_id}"


def make_author_books_key(author_id: int) -> str:
    return f"author:{author_id}:books"


def make_reviews_key(book_id: int) -> str:
    return f"book:{book_id}:reviews"


def cache_book(
    book_id: int, book_data: dict, r: Redis | None = None, ttl: int = DEFAULT_TTL
):
    r = r or get_redis()
    r.set(make_book_key(book_id), json.dumps(book_data), ex=ttl)


def get_book(book_id: int, r: Redis | None = None) -> dict | None:
    r = r or get_redis()
    raw = r.get(make_book_key(book_id))
    return json.loads(raw) if raw else None


def cache_author(
    author_id: int, author_data: dict, r: Redis | None = None, ttl: int = DEFAULT_TTL
):
    r = r or get_redis()
    r.set(make_author_key(author_id), json.dumps(author_data), ex=ttl)


def get_author(author_id: int, r: Redis | None = None) -> dict | None:
    r = r or get_redis()
    raw = r.get(make_author_key(author_id))
    return json.loads(raw) if raw else None


def cache_list(key: str, data: Any, r: Redis | None = None, ttl: int = DEFAULT_TTL):
    r = r or get_redis()
    r.set(key, json.dumps(data), ex=ttl)


def get_list(key: str, r: Redis | None = None) -> Any | None:
    r = r or get_redis()
    raw = r.get(key)
    return json.loads(raw) if raw else None


def cache_list_with_params(
    key: str,
    data: Any,
    params_payload: str,
    r: Redis | None = None,
    ttl: int = DEFAULT_TTL,
):
    """Store list data alongside normalized params to guard against collisions."""
    cache_list(key, {"data": data, "_params": params_payload}, r=r, ttl=ttl)


def get_list_with_params(
    key: str, expected_params_payload: str, r: Redis | None = None
) -> Any | None:
    """Return cached list only if params match; otherwise treat as miss."""
    cached = get_list(key, r=r)
    if isinstance(cached, dict) and cached.get("_params") == expected_params_payload:
        return cached.get("data")
    return None


def link_book_to_authors(
    book_id: int, author_ids: Iterable[int], r: Redis | None = None
):
    r = r or get_redis()
    for aid in author_ids:
        r.sadd(make_author_books_key(aid), book_id)


def get_books_for_author(author_id: int, r: Redis | None = None) -> set[int]:
    r = r or get_redis()
    return {int(bid) for bid in r.smembers(make_author_books_key(author_id))}


def invalidate_book(book_id: int, r: Redis | None = None):
    r = r or get_redis()
    r.delete(make_book_key(book_id))
    r.delete(make_reviews_key(book_id))
    r.delete(f"book:{book_id}:authors")


def invalidate_author(
    author_id: int, r: Redis | None = None, book_ids: Iterable[int] | None = None
):
    r = r or get_redis()
    r.delete(make_author_key(author_id))
    author_books_key = make_author_books_key(author_id)
    related_book_ids = {int(bid) for bid in book_ids} if book_ids else set()
    if not related_book_ids:
        related_book_ids = {int(bid) for bid in r.smembers(author_books_key)}

    if related_book_ids:
        keys_to_delete = [make_book_key(bid) for bid in related_book_ids]
        review_keys = [make_reviews_key(bid) for bid in related_book_ids]
        r.delete(*(keys_to_delete + review_keys))

    r.delete(author_books_key)
