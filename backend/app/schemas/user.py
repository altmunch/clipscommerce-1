from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    isActive: bool
    createdAt: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    accessToken: str
    tokenType: str = "bearer"