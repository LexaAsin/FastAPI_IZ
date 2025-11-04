from pony.orm import *
from database.db import db
from datetime import datetime

class User(db.Entity):
    id = PrimaryKey(int, auto=True)
    email = Required(str, unique=True)
    hashed_password = Required(str)
    created_at = Required(datetime, default=datetime.now)
    # Связи с другими таблицами
    books = Set('Book', reverse='owner')
    comments = Set('Comment', reverse='user')
    notes = Set('Note', reverse='user')

class Author(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    bio = Optional(str)
    # Связь с книгами
    books = Set('Book', reverse='author')

class Book(db.Entity):
    id = PrimaryKey(int, auto=True)
    title = Required(str)
    description = Optional(str)
    year = Optional(int)
    # Связи
    author = Required(Author, reverse='books')
    owner = Required(User, reverse='books')
    comments = Set('Comment', reverse='book')
    notes = Set('Note', reverse='book')
    genres = Set('Genre', reverse='books')
    files = Set('File', reverse='book')  # Добавили обратную связь

class Genre(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str, unique=True)
    books = Set(Book, reverse='genres')

class Comment(db.Entity):
    id = PrimaryKey(int, auto=True)
    text = Required(str)
    created_at = Required(datetime, default=datetime.now)
    # Связи
    user = Required(User, reverse='comments')
    book = Required(Book, reverse='comments')

class Note(db.Entity):
    id = PrimaryKey(int, auto=True)
    text = Required(str)
    created_at = Required(datetime, default=datetime.now)
    # Связи
    user = Required(User, reverse='notes')
    book = Required(Book, reverse='notes')

class File(db.Entity):
    id = PrimaryKey(int, auto=True)
    filename = Required(str)
    file_path = Required(str)
    uploaded_at = Required(datetime, default=datetime.now)
    # Связь с книгой (например, обложка или PDF)
    book = Optional(Book, reverse='files')  # Добавили reverse