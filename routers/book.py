from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import asc, desc, func, or_, select, text
from models import Author, Book, Review
from database import get_db
from dependencies import parse_sort
from schemas.book import BookCreate, BookDetailRead, BookListRead, BookUpdate, BookSortControl, SortField, SortDirection
from schemas.review import ReviewCreate, ReviewRead

router = APIRouter(prefix='/books', tags=['books'])

@router.get('/', response_model=List[BookListRead])
def get_books(
    q: str | None = Query(None, description="Full-text query"),
    title: str | None = Query(None, description="Exact title filter"),
    isbn: str | None = Query(None, description="Exact ISBN filter"),
    author_id: int | None = Query(None, description="Filter by author id"),
    before : int | None = Query(None, description="Filter by Year(before)"),
    after : int | None = Query(None, description="Filter by Year(after)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort : List[BookSortControl] = Depends(parse_sort),
    db: Session = Depends(get_db),
    ):
    stmt = (
        select(Book)
        .options(selectinload(Book.authors))
    )

    if title:
        stmt = stmt.where(Book.title == title)
    if isbn:
        stmt = stmt.where(Book.book_isbn == isbn)
    if author_id:
        stmt = stmt.where(Book.authors.any(Author.id == author_id))
    if before:
        stmt = stmt.where(Book.year <= before)
    if after:
        stmt = stmt.where(Book.year >= after)
    
    if q:
        tsq = func.websearch_to_tsquery("english", q)
        fts_score = func.ts_rank(Book.search_tsv, tsq)
        title_sim = func.similarity(Book.title, q)
        author_sim = func.coalesce(func.max(func.similarity(Author.name, q)), 0.0)
        total = 0.6 * fts_score + 0.25 * title_sim + 0.15 * author_sim
        stmt = (
            stmt
            .join(Book.authors, isouter=True)
            .where(or_(Book.search_tsv.op("@@")(tsq), Book.title.op("%")(q), Author.name.op("%")(q)))
            .group_by(Book.id)
            .add_columns(
                fts_score.label("fts_score"),
                title_sim.label("title_sim"),
                author_sim.label("author_sim"),
                total.label("total_score"),
            )
        )
    
    for s in sort:
        if s.sort_field is SortField.by_similarity:
            if not q:
                raise HTTPException(status_code=400, detail='Only work with q')
            col = text("total_score")
        elif s.sort_direction is SortField.by_title:
            col = Book.title
        elif s.sort_field is SortField.by_year:
            col = Book.year
        else:
            continue
        stmt = stmt.order_by(
            asc(col) if s.sort_direction is SortDirection.asc else desc(col)
        )
    
    stmt = stmt.limit(limit).offset(offset)
    books = db.execute(stmt).scalars().unique().all()
    return books


@router.get('/{book_id}', response_model=BookDetailRead)
def get_book(book_id: int, db : Session = Depends(get_db)):
    stat = (
        select(Book)
        .options(selectinload(Book.authors))
        .options(selectinload(Book.reviews))
        .where(Book.id == book_id)
    )
    book = db.execute(stat).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return  book

@router.get('/{book_id}/reviews', response_model=List[ReviewRead])
def get_reviews(book_id: int, db : Session = Depends(get_db)):
    stat = (
        select(Book)
        .options(selectinload(Book.reviews))
        .where(Book.id == book_id)
    )
    book = db.execute(stat).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book.reviews

@router.post('/', response_model=BookDetailRead)
def create_book(book : BookCreate, db : Session = Depends(get_db)):
    new_book = Book(
        title=book.title,
        year=book.year,
        book_isbn=book.book_isbn,
        genre_name=book.genre_name,
        description=book.description,
    )

    if book.author_ids:
        author_ids = set(book.author_ids)
        stmt_authors = select(Author).where(Author.id.in_(author_ids))
        authors = db.execute(stmt_authors).scalars().all()

        if len(authors) != len(author_ids):
            raise HTTPException(status_code=400, detail="At least one author id does not exist.")

        new_book.authors = list(authors)
    else:
        new_book.authors = []

    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book

@router.post('/{book_id}/reviews', response_model=ReviewRead)
def create_review(book_id : int, review : ReviewCreate, db : Session = Depends(get_db)):
    stat_book = (
        select(Book)
        .options(selectinload(Book.authors))
        .options(selectinload(Book.reviews))
        .where(Book.id == book_id)
    )
    book = db.execute(stat_book).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    dup_check = (
        select(Review)
        .where(Review.book_id == book_id, Review.reviewer_name == review.reviewer_name)
    )
    if db.execute(dup_check).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Reviewer has already reviewed this book.")
    new_review = Review(
        book_id=book_id,
        reviewer_name=review.reviewer_name,
        rating=review.rating,
        comment=review.comment,
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

@router.put('/{book_id}', response_model=BookDetailRead)
def replace_book(book_id: int , new_book : BookCreate, db : Session = Depends(get_db)):
    stat = (
        select(Book)
        .options(selectinload(Book.authors))
        .options(selectinload(Book.reviews))
        .where(Book.id == book_id)
    )
    old_book = db.execute(stat).scalar_one_or_none()
    if not old_book:
        raise HTTPException(status_code=404, detail='Book not found')

    if new_book.author_ids:
        author_ids = set(new_book.author_ids)
        stmt_authors = select(Author).where(Author.id.in_(author_ids))
        authors = db.execute(stmt_authors).scalars().all()

        if len(authors) != len(author_ids):
            raise HTTPException(status_code=400, detail="At least one author id does not exist.")

        old_book.authors = list(authors)
    else:
        old_book.authors = []
    
    old_book.title = new_book.title
    old_book.year = new_book.year
    old_book.book_isbn = new_book.book_isbn
    old_book.genre_name = new_book.genre_name
    old_book.description = new_book.description
    # old_book.reviews = []
    db.commit()
    db.refresh(old_book)
    return old_book

@router.put('/{book_id}/authors', response_model=BookDetailRead)
def update_author_list(book_id : int, new_author_list : list[int], db : Session = Depends(get_db)):
    stat_book = (
        select(Book)
        .options(selectinload(Book.authors))
        .options(selectinload(Book.reviews))
        .where(Book.id == book_id)
        )
    book = db.execute(stat_book).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail='Cant find the book')
    if not new_author_list:
        book.authors = []
    else:
        author_ids = set(new_author_list)
        stmt_authors = select(Author).where(Author.id.in_(author_ids))
        authors = db.execute(stmt_authors).scalars().all()

        if len(author_ids) != len(authors):
            raise HTTPException(status_code=400, detail="At least one author id does not exist.")
        
        book.authors = list(authors)
    db.commit()
    db.refresh(book)
    return book

@router.patch('/{book_id}', response_model=BookDetailRead)
def update_book(book_id: int , new_book : BookUpdate, db : Session = Depends(get_db)):
    stat = (
        select(Book)
        .options(selectinload(Book.authors))
        .options(selectinload(Book.reviews))
        .where(Book.id == book_id)
    )
    old_book = db.execute(stat).scalar_one_or_none()

    if not old_book:
        raise HTTPException(status_code=404, detail='Book not found')

    update_data = new_book.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(old_book, key, val)

    db.commit()
    db.refresh(old_book)
    return old_book
