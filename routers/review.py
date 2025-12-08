from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from models import Review
from database import get_db

router = APIRouter(prefix='/reviews', tags=["reviews"])

@router.delete('/{review_id}', status_code=204)
def delete_review(review_id : int, db : Session = Depends(get_db)):
    stat = select(Review).where(Review.id == review_id)
    review = db.execute(stat).scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail='Review not found')
    db.delete(review)
    db.commit()