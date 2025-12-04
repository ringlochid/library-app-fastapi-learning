from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from ..models import Author, Book, Review
from ..database import get_db
from ..schemas.book import BookCreate, BookRead, BookUpdate

router = APIRouter(prefix='/books', tags=['books'])

@router.get('/', response_model=List[BookRead])
def get_books(db : Session = Depends(get_db)):
    stat = (
        select(Book)
        .options(selectinload(Book.authors))
        .options(selectinload(Book.reviews))
    )
    books = db.execute(stat).scalars().all()
    return books


@router.get('/{book_id}', response_model=BookRead)
def get_author(book_id: int, db : Session = Depends(get_db)):
    stat = (
        select(Book)
        .options(selectinload(Book.authors))
        .options(selectinload(Book.reviews))
        .where(Book.id == book_id)
    )
    book = db.execute(stat).scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Author not found")
    return  book


@router.post('/', response_model=BookRead)
def create_book(book : BookCreate, db : Session = Depends(get_db)):
    new_book = Book(
        title = book.title,
        year = book.year
    )

    if book.author_ids:
        stmt_authors = select(Author).where(Author.id.in_(book.author_ids))
        authors = db.execute(stmt_authors).scalars().all()

        if len(authors) != len(book.author_ids):
            raise HTTPException(status_code=400, detail="At least one author id does not exist.")

        new_book.authors = list(authors)
    else:
        new_book.authors = []

    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book

@router.put('/{book_id}', response_model=BookRead)
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
        stmt_authors = select(Author).where(Author.id.in_(new_book.author_ids))
        authors = db.execute(stmt_authors).scalars().all()

        if len(authors) != len(new_book.author_ids):
            raise HTTPException(status_code=400, detail="At least one author id does not exist.")

        old_book.authors = list(authors)
    else:
        old_book.authors = []
    
    old_book.title = new_book.title
    old_book.year = new_book.year
    # old_book.reviews = []
    db.commit()
    db.refresh(old_book)
    return old_book

@router.patch('/{book_id}', response_model=BookRead)
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

    if new_book.author_ids:
        stmt_authors = select(Author).where(Author.id.in_(new_book.author_ids))
        authors = db.execute(stmt_authors).scalars().all()

        if len(authors) != len(new_book.author_ids):
            raise HTTPException(status_code=400, detail="At least one author id does not exist.")

        old_book.authors = list(authors)
    else:
        old_book.authors = []

    update_data = new_book.model_dump(exclude={"author_ids"}, exclude_unset=True)
    for key, val in update_data.items():
        setattr(old_book, key, val)

    db.commit()
    db.refresh(old_book)
    return old_book