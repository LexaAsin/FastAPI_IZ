from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# User models
class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

# Author models
class AuthorCreate(BaseModel):
    name: str
    bio: Optional[str] = None

class AuthorResponse(BaseModel):
    id: int
    name: str
    bio: Optional[str] = None

    class Config:
        from_attributes = True

# Book models
class BookCreate(BaseModel):
    title: str
    description: Optional[str] = None
    year: Optional[int] = None
    author_id: int
    genres: Optional[List[int]] = None

class BookResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    year: Optional[int] = None
    author: AuthorResponse
    owner: UserResponse

    class Config:
        from_attributes = True

# Comment models
class CommentCreate(BaseModel):
    text: str
    book_id: int

class CommentResponse(BaseModel):
    id: int
    text: str
    created_at: datetime
    user: UserResponse
    book: BookResponse

    class Config:
        from_attributes = True

# Note models
class NoteCreate(BaseModel):
    text: str
    book_id: int

class NoteResponse(BaseModel):
    id: int
    text: str
    created_at: datetime
    user: UserResponse
    book: BookResponse

    class Config:
        from_attributes = True

# Genre models
class GenreCreate(BaseModel):
    name: str

class GenreResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

# File models
class FileCreate(BaseModel):
    filename: str
    file_path: str
    book_id: Optional[int] = None

class FileResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    uploaded_at: datetime
    book: Optional[BookResponse] = None

    class Config:
        from_attributes = True