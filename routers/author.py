from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from ..models import Author
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
    new_author