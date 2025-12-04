from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import get_db
from ..schemas.book import BookCreate, BookRead, BookUpdate