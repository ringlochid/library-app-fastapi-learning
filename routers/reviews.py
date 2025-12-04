from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import get_db
from ..schemas.review import ReviewCreate, ReviewRead, ReviewUpdate