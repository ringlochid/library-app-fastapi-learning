from sqlalchemy.dialects.postgresql import TSVECTOR
from database import Base
from sqlalchemy import Computed, Table, Column, String, Text, Integer, ForeignKey, CheckConstraint, UniqueConstraint
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

    __table_args__ = (
        CheckConstraint("email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'", name='ck_authors_email_format'),
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    book_isbn : Mapped[str | None] = mapped_column(String(14), index=True)
    genre_name : Mapped[str | None] = mapped_column(String(127), index=True)
    description : Mapped[str | None] = mapped_column(Text)

    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="book", cascade="all, delete-orphan")

    search_tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(genre_name, '')), 'B') || "
            "setweight(to_tsvector('english', coalesce(description, '')), 'C')",
            persisted=True,
        ),
    )

    __table_args__ = (
        CheckConstraint("year IS NULL OR year > 0", name="ck_books_year_positive"),
        CheckConstraint(
                            "book_isbn IS NULL OR char_length(book_isbn) IN (10, 13)",
                            name="ck_book_isbn_length",
                        ),
    )

    # many-to-many: books → authors
    authors: Mapped[list["Author"]] = relationship(
        secondary="author_book_relation",
        back_populates="books",
    )

class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    book: Mapped["Book"] = relationship("Book", back_populates="reviews")

    __table_args__ = (
        CheckConstraint("rating > 0 AND rating < 6", name="ck_reviews_rating_1_5"),
        UniqueConstraint("book_id", "reviewer_name", name="uq_reviews_book_reviewer"),
    )


author_book_relation = Table(
    "author_book_relation",
    Base.metadata,
    Column("author_id", ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
    Column("book_id",   ForeignKey("books.id", ondelete="CASCADE"),   primary_key=True),
)
