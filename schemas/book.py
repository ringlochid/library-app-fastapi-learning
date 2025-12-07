from typing import List
from pydantic import BaseModel, Field
from .shared import ReviewBase, AuthorBase

class BookCreate(BaseModel):
    title: str
    year: int | None = None
    book_isbn: str | None = None
    genre_name: str | None = None
    description: str | None = None
    author_ids: list[int] = Field(default_factory=list)

class BookUpdate(BaseModel):
    title: str | None = None
    year: int | None = None
    book_isbn: str | None = None
    genre_name: str | None = None
    description: str | None = None

class BookListRead(BaseModel):
    id: int
    title: str
    year: int | None
    book_isbn: str | None
    genre_name: str | None
    description: str | None
    authors: List[AuthorBase] = Field(default_factory=list)

    class Config:
        from_attributes = True

class BookDetailRead(BookListRead):
    reviews: List[ReviewBase] = Field(default_factory=list)