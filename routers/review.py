from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from models import Review
from database import get_db
from redis import Redis
from cache import get_redis, invalidate_book

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.delete("/{review_id}", status_code=204)
def delete_review(
    review_id: int, db: Session = Depends(get_db), r: Redis = Depends(get_redis)
):
    stat = (
        select(Review).options(selectinload(Review.book)).where(Review.id == review_id)
    )
    review = db.execute(stat).scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    book_id = review.book.id
    db.delete(review)
    db.commit()
    invalidate_book(book_id, r)
