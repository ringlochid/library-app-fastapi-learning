from pydantic import BaseModel

class AuthorBase(BaseModel):
    id: int
    name: str
    email: str | None = None

    class Config:
        from_attributes = True

class ReviewBase(BaseModel):
    rating: int
    comment: str | None = None

    class Config:
        from_attributes = True

class BookBase(BaseModel):
    id: int
    title: str
    year: int | None

    class Config:
        from_attributes = True
