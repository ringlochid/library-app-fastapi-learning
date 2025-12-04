from pydantic import BaseModel
from .shared import BookBase

class ReviewCreate(BaseModel):
    book_id : int
    reviewer_name : str
    rating : int
    comment : str | None = None

class ReviewUpdate(BaseModel):
    book_id : int | None = None
    reviewer_name : str | None = None
    rating : int | None = None
    comment : str | None = None

class ReviewRead(BaseModel):
    id : int
    book_id : int
    reviewer_name : str
    rating : int
    comment : str | None = None

    book : BookBase

    class Config:
        from_attributes = True