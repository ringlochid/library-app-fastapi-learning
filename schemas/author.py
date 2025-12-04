from typing import List
from pydantic import BaseModel, Field
from .shared import BookBase

class AuthorCreate(BaseModel):
    name : str
    email: str | None = None
    book_ids: list[int] | None = None

class AuthorUpdate(BaseModel):
    name : str | None
    email : str | None
    book_ids: list[int] | None = None

class AuthorRead(BaseModel):
    id : int
    name : str
    email : str | None
    books: List[BookBase] = Field(default_factory=list)

    class Config:
        from_attributes = True