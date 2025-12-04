from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from ..models import Review
from ..database import get_db
from ..schemas.review import ReviewCreate, ReviewRead, ReviewUpdate

router = APIRouter(prefix='/reviews')

@router.delete('/{review_id}')
def delete_review(review_id : int):