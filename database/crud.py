from pony.orm import db_session, select, commit
from database.models import *
from auth import hash_password, verify_password
from typing import List, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Простое кэширование для часто запрашиваемых данных
class SimpleCache:
    def __init__(self):
        self._cache = {}
        self._timestamps = {}

    def get(self, key):
        if key in self._cache:
            if datetime.now() - self._timestamps[key] < timedelta(minutes=5):
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamps[key]
        return None

    def set(self, key, value):
        self._cache[key] = value
        self._timestamps[key] = datetime.now()

cache = SimpleCache()

# Кэшированные версии функций
@db_session
def get_all_authors_cached():
    cache_key = "all_authors"
    cached = cache.get(cache_key)
    if cached:
        logger.info("Returning cached authors")
        return cached
    authors = list(Author.select())
    cache.set(cache_key, authors)
    return authors

@db_session
def get_all_genres_cached():
    cache_key = "all_genres"
    cached = cache.get(cache_key)
    if cached:
        logger.info("Returning cached genres")
        return cached
    genres = list(Genre.select())
    cache.set(cache_key, genres)
    return genres

# User CRUD
@db_session
def create_user(email: str, password: str):
    existing_user = User.get(email=email)
    if existing_user:
        logger.warning(f"Registration failed - email already exists: {email}")
        return None
    hashed_pwd = hash_password(password)
    user = User(email=email, hashed_password=hashed_pwd)
    commit()
    logger.info(f"User registered: {email} (ID: {user.id})")
    return user

@db_session
def get_user_by_email(email: str):
    return User.get(email=email)

@db_session
def get_user_by_id(user_id: int):
    return User.get(id=user_id)

@db_session
def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# Author CRUD
@db_session
def create_author(name: str, bio: Optional[str] = None):
    author = Author(name=name, bio=bio)
    commit()
    return author

@db_session
def get_author(author_id: int):
    return Author.get(id=author_id)

@db_session
def get_all_authors():
    return list(Author.select())

@db_session
def update_author(author_id: int, name: Optional[str] = None, bio: Optional[str] = None):
    author = Author.get(id=author_id)
    if author:
        if name: author.name = name
        if bio: author.bio = bio
        commit()
    return author

@db_session
def delete_author(author_id: int):
    author = Author.get(id=author_id)
    if author:
        author.delete()
        commit()
    return author

# Book CRUD
@db_session
def create_book(title: str, author_id: int, owner_id: int, description: Optional[str] = None, year: Optional[int] = None):
    author = Author.get(id=author_id)
    owner = User.get(id=owner_id)
    if not author or not owner:
        logger.warning(f"Book creation failed - author {author_id} or owner {owner_id} not found")
        return None
    book = Book(title=title, author=author, owner=owner, description=description, year=year)
    commit()
    logger.info(f"Book created: {title} by {author.name} (Owner: {owner.email})")
    return book

@db_session
def get_book(book_id: int):
    return Book.get(id=book_id)

@db_session
def get_user_books(user_id: int):
    all_books = list(Book.select())
    return [b for b in all_books if b.owner.id == user_id]

@db_session
def get_all_books():
    return list(Book.select())

@db_session
def update_book(book_id: int, title: Optional[str] = None, description: Optional[str] = None, year: Optional[int] = None):
    book = Book.get(id=book_id)
    if book:
        if title: book.title = title
        if description: book.description = description
        if year: book.year = year
        commit()
    return book

@db_session
def delete_book(book_id: int):
    book = Book.get(id=book_id)
    if book:
        book.delete()
        commit()
    return book

# Comment CRUD
@db_session
def create_comment(text: str, book_id: int, user_id: int):
    book = Book.get(id=book_id)
    user = User.get(id=user_id)
    if not book or not user:
        return None
    comment = Comment(text=text, book=book, user=user)
    commit()
    return comment

@db_session
def get_book_comments(book_id: int):
    all_comments = list(Comment.select())
    return [c for c in all_comments if c.book.id == book_id]

@db_session
def delete_comment(comment_id: int):
    comment = Comment.get(id=comment_id)
    if comment:
        comment.delete()
        commit()
    return comment

# Note CRUD
@db_session
def create_note(text: str, book_id: int, user_id: int):
    book = Book.get(id=book_id)
    user = User.get(id=user_id)
    if not book or not user:
        return None
    note = Note(text=text, book=book, user=user)
    commit()
    return note

@db_session
def get_user_notes(user_id: int):
    all_notes = list(Note.select())
    return [n for n in all_notes if n.user.id == user_id]

# Genre CRUD
@db_session
def create_genre(name: str):
    genre = Genre(name=name)
    commit()
    return genre

@db_session
def get_all_genres():
    return list(Genre.select())

# File CRUD
@db_session
def create_file(filename: str, file_path: str, book_id: Optional[int] = None):
    book = Book.get(id=book_id) if book_id else None
    file = File(filename=filename, file_path=file_path, book=book)
    commit()
    return file