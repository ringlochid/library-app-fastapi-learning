from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from ..models import Author, Book
from ..database import get_db
from ..schemas.author import AuthorCreate, AuthorRead, AuthorUpdate

router = APIRouter(prefix='/author', tags=['authors'])

@router.get('/', response_model=List[AuthorRead])
def get_authors(db : Session = Depends(get_db)):
    stat = (
        select(Author)
        .options(selectinload(Author.books))
    )
    authors = db.execute(stat).scalars().all()
    return authors

@router.get('/{author_id}', response_model=AuthorRead)
def get_author(author_id: int, db : Session = Depends(get_db)):
    stat = (
        select(Author)
        .options(selectinload(Author.books))
        .where(Author.id == author_id)
    )
    author = db.execute(stat).scalar_one_or_none()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return  author

@router.post('/', response_model=AuthorRead)
def create_author(author : AuthorCreate, db : Session = Depends(get_db)):
    new_author = Author(
        name = author.name,
        email = author.email
    )
    if author.book_ids:
        stat_books = select(Book).where(Book.id.in_(author.book_ids))
        books = db.execute(stat_books).scalars().all()

        if len(books) != len(author.book_ids):
            raise HTTPException(status_code=400, detail='At least one book not match.')
        db.add(new_author)
        db.commit()
        db.refresh(new_author)
        return new_author

@router.put('/{author_id}', response_model=AuthorRead)
def replace_author(author_id: int , new_author : AuthorCreate, db : Session = Depends(get_db)):
    stat = select(Author).options(selectinload(Author.books)).where(Author.id == author_id)
    old_author = db.execute(stat).scalar_one_or_none()
    if not old_author:
        raise HTTPException(status_code=404, detail='Autahor not found')

    if new_author.book_ids:
        stat_books = select(Book).where(Book.id.in_(new_author.book_ids))
        books = db.execute(stat_books).scalars().all()

        if len(books) != len(new_author.book_ids):
            raise HTTPException(status_code=500, detail='At least one book not match.')
        
        old_author.books = list(books)
    else:
        old_author.books = []
    
    old_author.name = new_author.name
    old_author.email = new_author.email
    db.commit()
    db.refresh(old_author)
    return old_author

@router.patch('/{author_id}', response_model=AuthorRead)
def update_author(author_id: int, new_author: AuthorUpdate, db: Session = Depends(get_db)):
    stmt = (
        select(Author)
        .options(selectinload(Author.books))
        .where(Author.id == author_id)
    )
    old_author = db.execute(stmt).scalar_one_or_none()
    if not old_author:
        raise HTTPException(status_code=404, detail="Author not found")
    
    if new_author.book_ids is not None:
        stmt_books = select(Book).where(Book.id.in_(new_author.book_ids))
        books = db.execute(stmt_books).scalars().all()

        if len(books) != len(new_author.book_ids):
            raise HTTPException(status_code=400, detail="At least one book id does not exist")

        old_author.books = list(books)

    update_data = new_author.model_dump(exclude={"book_ids"}, exclude_none=True)
    for key, val in update_data.items():
        setattr(old_author, key, val)

    db.commit()
    db.refresh(old_author)
    return old_author

