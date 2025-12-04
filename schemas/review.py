from pydantic import BaseModel, Field

class ReviewCreate(BaseModel):
    reviewer_name: str
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None

class ReviewUpdate(BaseModel):
    reviewer_name: str | None = None
    rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = None

class ReviewRead(BaseModel):
    id: int
    reviewer_name: str
    rating: int
    comment: str | None = None

    class Config:
        from_attributes = True
