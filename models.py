from database import Base
from sqlalchemy import Table, Column, String,Text, Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str | None] = mapped_column(String(50))

    # many-to-many: authors → books
    books: Mapped[list["Book"]] = relationship(
        secondary="author_book_relation",
        back_populates="authors",
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer)

    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="book")

    __table_args__ = (
        CheckConstraint("year IS NULL OR year > 0", name="ck_books_year_positive"),
    )

    # many-to-many: books → authors
    authors: Mapped[list["Author"]] = relationship(
        secondary="author_book_relation",
        back_populates="books",
    )

class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), ondelete="CASCADE", nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    book: Mapped["Book"] = relationship("Book", back_populates="reviews")

    __table_args__ = (
        CheckConstraint("rating > 0 AND rating < 6", name="ck_reviews_rating_1_5"),
    )


author_book_relation = Table(
    "author_book_relation",
    Base.metadata,
    Column("author_id", ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
    Column("book_id",   ForeignKey("books.id", ondelete="CASCADE"),   primary_key=True),
)
