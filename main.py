from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response, JSONResponse
from database.db import db
from pony.orm import db_session, select, count
from database.models import *
from database import crud
from pydantic_models import *
from auth import create_token, verify_token, hash_password, verify_password
from typing import Optional
import logging
from datetime import datetime, timedelta
import csv
import json
from io import StringIO
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import PlainTextResponse

db.bind(provider='sqlite', filename='database/database.sqlite', create_db=True)
db.generate_mapping(create_tables=True)

app = FastAPI(
    title="Личная библиотека🫰",
    description="API для управления личной библиотекой книг",
    openapi_tags=[
        {
            "name": "🔐 Аутентификация",
            "description": "Регистрация и вход пользователей",
        },
        {
            "name": "📚 Авторы",
            "description": "Управление авторами книг",
        },
        {
            "name": "📖 Книги",
            "description": "Операции с книгами",
        },
        {
            "name": "💬 Комментарии",
            "description": "Комментарии к книгам",
        },
        {
            "name": "🏷️ Жанры",
            "description": "Управление жанрами",
        },
        {
            "name": "📝 Заметки",
            "description": "Личные заметки к книгам",
        },
        {
            "name": "📎 Файлы",
            "description": "Прикрепленные файлы",
        },
        {
            "name": "📊 Админка",
            "description": "Административные функции",
        },
        {
            "name": "📤 Экспорт",
            "description": "Экспорт данных",
        }
    ]
)

security = HTTPBearer()

app.add_middleware(GZipMiddleware, minimum_size=1000)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

rate_limit_cache = {}


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    now = datetime.now()

    if client_ip in rate_limit_cache:
        requests, first_request = rate_limit_cache[client_ip]
        if now - first_request < timedelta(minutes=1):
            if requests >= 100:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests"}
                )
            rate_limit_cache[client_ip] = (requests + 1, first_request)
        else:
            rate_limit_cache[client_ip] = (1, now)
    else:
        rate_limit_cache[client_ip] = (1, now)

    response = await call_next(request)
    return response

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    user = crud.get_user_by_id(payload.get("user_id"))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user


# АУТЕНТИФИКАЦИЯ
@app.post("/register", response_model=UserResponse, tags=["🔐 Аутентификация"])
@db_session
def register(user_data: UserCreate):
    user = crud.create_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return user


@app.post("/login", tags=["🔐 Аутентификация"])
@db_session
def login(user_data: UserCreate):
    user = crud.authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"user_id": user.id})
    return {"access_token": token, "token_type": "bearer"}


# СОЗДАНИЕ ДАННЫХ
@app.post("/authors", response_model=AuthorResponse, tags=["📚 Авторы"])
@db_session
def create_author(author_data: AuthorCreate, current_user: User = Depends(get_current_user)):
    author = crud.create_author(author_data.name, author_data.bio)
    return author


@app.post("/books", response_model=BookResponse, tags=["📖 Книги"])
@db_session
def create_book(book_data: BookCreate, current_user: User = Depends(get_current_user)):
    book = crud.create_book(
        title=book_data.title,
        author_id=book_data.author_id,
        owner_id=current_user.id,
        description=book_data.description,
        year=book_data.year
    )
    if not book:
        raise HTTPException(status_code=404, detail="Author not found")
    return book


@app.post("/comments", response_model=CommentResponse, tags=["💬 Комментарии"])
@db_session
def create_comment(comment_data: CommentCreate, current_user: User = Depends(get_current_user)):
    comment = crud.create_comment(
        text=comment_data.text,
        book_id=comment_data.book_id,
        user_id=current_user.id
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Book not found")

    # Преобразуем в словарь
    return {
        "id": comment.id,
        "text": comment.text,
        "created_at": comment.created_at,
        "user": {
            "id": comment.user.id,
            "email": comment.user.email,
            "created_at": comment.user.created_at
        },
        "book": {
            "id": comment.book.id,
            "title": comment.book.title,
            "description": comment.book.description,
            "year": comment.book.year,
            "author": {
                "id": comment.book.author.id,
                "name": comment.book.author.name,
                "bio": comment.book.author.bio
            },
            "owner": {
                "id": comment.book.owner.id,
                "email": comment.book.owner.email,
                "created_at": comment.book.owner.created_at
            }
        }
    }

@app.post("/genres", response_model=GenreResponse, tags=["🏷️ Жанры"])
@db_session
def create_genre(genre_data: GenreCreate, current_user: User = Depends(get_current_user)):
    genre = crud.create_genre(genre_data.name)
    return genre

@app.post("/notes", response_model=NoteResponse, tags=["📝 Заметки"])
@db_session
def create_note(note_data: NoteCreate, current_user: User = Depends(get_current_user)):
    note = crud.create_note(
        text=note_data.text,
        book_id=note_data.book_id,
        user_id=current_user.id
    )
    if not note:
        raise HTTPException(status_code=404, detail="Book not found")

    return {
        "id": note.id,
        "text": note.text,
        "created_at": note.created_at,
        "user": {
            "id": note.user.id,
            "email": note.user.email,
            "created_at": note.user.created_at
        },
        "book": {
            "id": note.book.id,
            "title": note.book.title,
            "description": note.book.description,
            "year": note.book.year,
            "author": {
                "id": note.book.author.id,
                "name": note.book.author.name,
                "bio": note.book.author.bio
            },
            "owner": {
                "id": note.book.owner.id,
                "email": note.book.owner.email,
                "created_at": note.book.owner.created_at
            }
        }
    }


@app.post("/files", response_model=FileResponse, tags=["📎 Файлы"])
@db_session
def create_file(file_data: FileCreate, current_user: User = Depends(get_current_user)):
    file = crud.create_file(
        filename=file_data.filename,
        file_path=file_data.file_path,
        book_id=file_data.book_id
    )
    return file


# ПОЛУЧЕНИЕ ДАННЫХ
@app.get("/books", response_model=list[BookResponse], tags=["📖 Книги"])
@db_session
def get_books(current_user: User = Depends(get_current_user)):
    books = crud.get_user_books(current_user.id)
    books_data = []
    for book in books:
        books_data.append({
            "id": book.id,
            "title": book.title,
            "description": book.description,
            "year": book.year,
            "created_at": book.created_at if hasattr(book, 'created_at') else datetime.now(),
            "author": {
                "id": book.author.id,
                "name": book.author.name,
                "bio": book.author.bio
            },
            "owner": {
                "id": book.owner.id,
                "email": book.owner.email,
                "created_at": book.owner.created_at
            }
        })
    return books_data


# ФИЛЬТРАЦИЯ
@app.get("/books/filter", response_model=list[BookResponse], tags=["📖 Книги"])
@db_session
def get_books_filtered(
        current_user: User = Depends(get_current_user),
        author_name: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        sort_by: Optional[str] = "title",
        sort_order: Optional[str] = "asc"
):
    all_books = list(Book.select())
    books = [b for b in all_books if b.owner.id == current_user.id]

    if author_name:
        books = [b for b in books if b.author.name.lower() == author_name.lower()]

    if year_from:
        books = [b for b in books if b.year and b.year >= year_from]
    if year_to:
        books = [b for b in books if b.year and b.year <= year_to]

    if sort_by == "title":
        books.sort(key=lambda x: x.title, reverse=(sort_order == "desc"))
    elif sort_by == "year":
        books.sort(key=lambda x: x.year or 0, reverse=(sort_order == "desc"))
    elif sort_by == "author":
        books.sort(key=lambda x: x.author.name, reverse=(sort_order == "desc"))

    books_data = []
    for book in books:
        books_data.append({
            "id": book.id,
            "title": book.title,
            "description": book.description,
            "year": book.year,
            "created_at": book.created_at if hasattr(book, 'created_at') else datetime.now(),
            "author": {
                "id": book.author.id,
                "name": book.author.name,
                "bio": book.author.bio
            },
            "owner": {
                "id": book.owner.id,
                "email": book.owner.email,
                "created_at": book.owner.created_at
            }
        })

    return books_data


@app.get("/books/{book_id}", response_model=BookResponse, tags=["📖 Книги"])
@db_session
def get_book(book_id: int, current_user: User = Depends(get_current_user)):
    book = crud.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.owner.id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your book")

    return {
        "id": book.id,
        "title": book.title,
        "description": book.description,
        "year": book.year,
        "created_at": book.created_at if hasattr(book, 'created_at') else datetime.now(),
        "author": {
            "id": book.author.id,
            "name": book.author.name,
            "bio": book.author.bio
        },
        "owner": {
            "id": book.owner.id,
            "email": book.owner.email,
            "created_at": book.owner.created_at
        }
    }


@app.get("/authors", response_model=list[AuthorResponse], tags=["📚 Авторы"])
@db_session
def get_authors(current_user: User = Depends(get_current_user)):
    authors = crud.get_all_authors()
    return authors


@app.get("/authors/{author_id}", response_model=AuthorResponse, tags=["📚 Авторы"])
@db_session
def get_author(author_id: int, current_user: User = Depends(get_current_user)):
    author = crud.get_author(author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    return author


@app.get("/genres", response_model=list[GenreResponse], tags=["🏷️ Жанры"])
@db_session
def get_genres(current_user: User = Depends(get_current_user)):
    genres = crud.get_all_genres()
    return genres


@app.get("/books/{book_id}/comments", response_model=list[CommentResponse], tags=["💬 Комментарии"])
@db_session
def get_book_comments(book_id: int, current_user: User = Depends(get_current_user)):
    comments = crud.get_book_comments(book_id)

    comments_data = []
    for comment in comments:
        comments_data.append({
            "id": comment.id,
            "text": comment.text,
            "created_at": comment.created_at,
            "user": {
                "id": comment.user.id,
                "email": comment.user.email,
                "created_at": comment.user.created_at
            },
            "book": {
                "id": comment.book.id,
                "title": comment.book.title,
                "description": comment.book.description,
                "year": comment.book.year,
                "author": {
                    "id": comment.book.author.id,
                    "name": comment.book.author.name,
                    "bio": comment.book.author.bio
                },
                "owner": {
                    "id": comment.book.owner.id,
                    "email": comment.book.owner.email,
                    "created_at": comment.book.owner.created_at
                }
            }
        })
    return comments_data

# АДМИН-ПАНЕЛЬ
@app.get("/admin/users", response_model=list[UserResponse], tags=["📊 Админка"])
@db_session
def get_all_users(current_user: User = Depends(get_current_user)):
    if current_user.id != 1:
        raise HTTPException(status_code=403, detail="Admin access required")

    users = list(User.select())
    users_data = []
    for user in users:
        users_data.append({
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at
        })
    return users_data


@app.get("/admin/statistics", tags=["📊 Админка"])
@db_session
def get_statistics(current_user: User = Depends(get_current_user)):
    if current_user.id != 1:
        raise HTTPException(status_code=403, detail="Admin access required")

    all_users = list(User.select())
    all_books = list(Book.select())
    all_authors = list(Author.select())

    total_users = len(all_users)
    total_books = len(all_books)
    total_authors = len(all_authors)

    return {
        "total_users": total_users,
        "total_books": total_books,
        "total_authors": total_authors,
        "books_per_user": total_books / total_users if total_users > 0 else 0
    }

# ==================== ЭКСПОРТ ДАННЫХ ====================
@app.get("/export/books/csv", tags=["📤 Экспорт"])
@db_session
def export_books_csv(current_user: User = Depends(get_current_user)):
    books = crud.get_user_books(current_user.id)

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["ID", "Title", "Author", "Year", "Description"])

    for book in books:
        writer.writerow([
            book.id,
            book.title,
            book.author.name,
            book.year or "",
            book.description or ""
        ])

    response = Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=my_books.csv"}
    )

    logger.info(f"User {current_user.email} exported books to CSV")
    return response


@app.get("/export/books/json", tags=["📤 Экспорт"])
@db_session
def export_books_json(current_user: User = Depends(get_current_user)):
    books = crud.get_user_books(current_user.id)

    books_data = []
    for book in books:
        books_data.append({
            "id": book.id,
            "title": book.title,
            "author": book.author.name,
            "year": book.year,
            "description": book.description,
            "created_at": book.created_at.isoformat() if hasattr(book, 'created_at') else None
        })

    logger.info(f"User {current_user.email} exported books to JSON")
    return {"books": books_data}


# ==================== КЭШИРОВАНИЕ ====================
@app.get("/cached/authors", include_in_schema=False)
@db_session
def get_cached_authors(current_user: User = Depends(get_current_user)):
    authors = crud.get_all_authors_cached()
    return authors


@app.get("/cached/genres", include_in_schema=False)
@db_session
def get_cached_genres(current_user: User = Depends(get_current_user)):
    genres = crud.get_all_genres_cached()
    return genres


@app.get("/", include_in_schema=False)
def read_root():
    return PlainTextResponse("ЧЕ НАДО?\n            БРАТ, НЕ НУЖНА ТЕБЕ ТАКАЯ МАШИНА")


# uvicorn main:app --reload