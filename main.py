from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import author, book, review

#from database import Base, engine
#Base.metadata.create_all(bind=engine) #for prototyping

app = FastAPI()

origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(author.router)
app.include_router(book.router)
app.include_router(review.router)