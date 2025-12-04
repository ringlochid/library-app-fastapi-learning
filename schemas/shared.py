from pydantic import BaseModel

class AuthorBase(BaseModel):
    name : str
    email : str | None

    class Config:
        from_attributes = True

class ReviewBase(BaseModel):
    reviewer_name : str
    rating : int
    comment : str | None = None

    class Config:
        from_attributes = True

class BookBase(BaseModel):
    title : str
    year : int | None

    class Config:
        from_attributes = True