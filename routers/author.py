from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, select, func
from models import Author, Book
from database import get_db
from schemas.author import AuthorCreate, AuthorRead, AuthorUpdate
from schemas.shared import BookBase
from redis import Redis
from cache import (
    bump_cache_version,
    cache_list,
    get_redis,
    make_author_books_key,
    make_authors_list_key,
    cache_author,
    cache_list_with_params,
    get_author,
    get_list,
    get_list_with_params,
    invalidate_author,
)

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("/", response_model=List[AuthorRead])
def get_authors_router(
    q: str | None = Query(None, description="Full-text query"),
    name: str | None = Query(None, description="Exact name filter"),
    email: str | None = Query(None, description="Exact email filter"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    r: Redis = Depends(get_redis),
):
    params = {"q": q, "name": name, "email": email, "limit": limit, "offset": offset}
    key, payload = make_authors_list_key(params, r=r)
    cached = get_list_with_params(key, payload, r)
    if cached is not None:
        return cached
    stat = select(Author).options(selectinload(Author.books))

    if name:
        stat = stat.where(Author.name == name)
    if email:
        stat = stat.where(Author.email == email)

    order_exp = []

    if q:
        norm_q = func.immutable_unaccent(q)
        name_sim = func.similarity(func.immutable_unaccent(Author.name), norm_q)
        email_sim = func.similarity(
            func.coalesce(func.immutable_unaccent(Author.email), ""), norm_q
        )
        total_score = 0.7 * name_sim + 0.3 * email_sim
        stat = stat.where(
            or_(
                func.immutable_unaccent(Author.name).op("%")(norm_q),
                func.immutable_unaccent(Author.email).op("%")(norm_q),
            )
        ).add_columns(total_score.label("total_score"))
        order_exp.append(total_score.desc())

    order_exp.append(Author.id.asc())
    stat = stat.order_by(*order_exp)
    stat = stat.limit(limit).offset(offset)
    authors = db.execute(stat).scalars().all()
    serialized = [
        AuthorRead.model_validate(a, from_attributes=True).model_dump() for a in authors
    ]
    cache_list_with_params(key, serialized, payload, r)
    return serialized


@router.get("/{author_id}", response_model=AuthorRead)
def get_author_router(
    author_id: int, db: Session = Depends(get_db), r: Redis = Depends(get_redis)
):
    cached = get_author(author_id, r)
    if cached is not None:
        return cached
    stat = (
        select(Author).options(selectinload(Author.books)).where(Author.id == author_id)
    )
    author = db.execute(stat).scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    serialized = AuthorRead.model_validate(author, from_attributes=True).model_dump()
    cache_author(author_id, serialized, r)
    return serialized


@router.get("/{author_id}/books", response_model=List[BookBase])
def get_author_books(
    author_id: int, db: Session = Depends(get_db), r: Redis = Depends(get_redis)
):
    key = make_author_books_key(author_id)
    cached = get_list(key, r)
    if cached is not None:
        return cached
    stat = (
        select(Author).options(selectinload(Author.books)).where(Author.id == author_id)
    )
    author = db.execute(stat).scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    payload = [BookBase.model_validate(b, from_attributes=True).model_dump() for b in author.books]
    cache_list(key, payload, r)
    return payload


@router.post("/", response_model=AuthorRead)
def create_author(
    author: AuthorCreate, db: Session = Depends(get_db), r: Redis = Depends(get_redis)
):
    book_ids = set(author.book_ids or [])
    new_author = Author(
        name=author.name,
        email=author.email,
    )

    if book_ids:
        stmt_books = select(Book).where(Book.id.in_(book_ids))
        books = db.execute(stmt_books).scalars().all()

        if len(books) != len(book_ids):
            raise HTTPException(
                status_code=400, detail="At least one book id does not exist."
            )

        new_author.books = list(books)
    else:
        new_author.books = []

    db.add(new_author)
    db.commit()
    db.refresh(new_author)
    if book_ids:
        invalidate_author(new_author.id, r, book_ids=book_ids)
        bump_cache_version("books:list", r)
    bump_cache_version("authors:list", r)
    return new_author


@router.put("/{author_id}", response_model=AuthorRead)
def replace_author(
    author_id: int,
    new_author: AuthorCreate,
    db: Session = Depends(get_db),
    r: Redis = Depends(get_redis),
):
    stat = (
        select(Author).options(selectinload(Author.books)).where(Author.id == author_id)
    )
    old_author = db.execute(stat).scalar_one_or_none()
    if not old_author:
        raise HTTPException(status_code=404, detail="Author not found")

    previous_book_ids = {book.id for book in old_author.books}

    if new_author.book_ids:
        book_ids = set(new_author.book_ids)
        stat_books = select(Book).where(Book.id.in_(book_ids))
        books = db.execute(stat_books).scalars().all()

        if len(books) != len(book_ids):
            raise HTTPException(
                status_code=400, detail="At least one book id does not exist."
            )
        old_author.books = list(books)
    else:
        book_ids = set()
        old_author.books = []

    old_author.name = new_author.name
    old_author.email = new_author.email
    db.commit()
    affected_book_ids = previous_book_ids | book_ids
    invalidate_author(author_id, r, book_ids=affected_book_ids)
    bump_cache_version("authors:list", r)
    if affected_book_ids:
        bump_cache_version("books:list", r)
    db.refresh(old_author)
    return old_author


@router.patch("/{author_id}", response_model=AuthorRead)
def update_author(
    author_id: int,
    new_author: AuthorUpdate,
    db: Session = Depends(get_db),
    r: Redis = Depends(get_redis),
):
    stmt = (
        select(Author).options(selectinload(Author.books)).where(Author.id == author_id)
    )
    old_author = db.execute(stmt).scalar_one_or_none()
    if not old_author:
        raise HTTPException(status_code=404, detail="Author not found")

    previous_book_ids = {book.id for book in old_author.books}
    updated_book_ids = previous_book_ids

    if new_author.book_ids is not None:
        if new_author.book_ids:
            book_ids = set(new_author.book_ids)
            stmt_books = select(Book).where(Book.id.in_(book_ids))
            books = db.execute(stmt_books).scalars().all()

            if len(books) != len(book_ids):
                raise HTTPException(
                    status_code=400, detail="At least one book id does not exist"
                )
            old_author.books = list(books)
            updated_book_ids = book_ids
        else:
            updated_book_ids = set()
            old_author.books = []

    update_data = new_author.model_dump(exclude={"book_ids"}, exclude_unset=True)
    for key, val in update_data.items():
        setattr(old_author, key, val)

    db.commit()
    affected_book_ids = previous_book_ids | updated_book_ids
    invalidate_author(author_id, r, book_ids=affected_book_ids)
    bump_cache_version("authors:list", r)
    if affected_book_ids:
        bump_cache_version("books:list", r)
    db.refresh(old_author)
    return old_author


@router.delete("/{author_id}", status_code=204)
def del_author(author_id, db: Session = Depends(get_db), r: Redis = Depends(get_redis)):
    stat = (
        select(Author).options(selectinload(Author.books)).where(Author.id == author_id)
    )
    author = db.execute(stat).scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=404, detail="author not found")
    book_ids = {b.id for b in author.books}
    db.delete(author)
    db.commit()
    invalidate_author(author_id, r, book_ids=book_ids)
    bump_cache_version("authors:list", r)
    if book_ids:
        bump_cache_version("books:list", r)
