from typing import List
from pydantic import BaseModel, Field
from .shared import ReviewBase, AuthorBase

class BookCreate(BaseModel):
    title : str
    year : int | None = None
    author_ids : list | None = []

class BookUpdate(BaseModel):
    title : str | None
    year : int | None
    author_ids : list | None = []

class BookRead(BaseModel):
    title : str
    year : int | None
    authors: List[AuthorBase] = Field(default_factory=list)
    reviews: List[ReviewBase] = Field(default_factory=list)
    
    class Config:
        from_attributes = True