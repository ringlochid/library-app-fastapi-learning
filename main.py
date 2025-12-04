from fastapi import FastAPI
from database import Base, engine
from routers import author, book

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(author.router)
app.include_router(book.router)
