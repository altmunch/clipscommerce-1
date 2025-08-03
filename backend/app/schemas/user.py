from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional
import re

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Valid email address")

class UserCreate(UserBase):
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="Password must be 8-128 characters"
    )
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password complexity"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        # Check for common weak passwords
        weak_passwords = {'password', '12345678', 'qwerty123', 'admin123'}
        if v.lower() in weak_passwords:
            raise ValueError('Password is too common and weak')
        
        return v
    
    @validator('email')
    def validate_email(cls, v):
        """Additional email validation"""
        email_str = str(v).lower()
        
        # Block common temporary email domains
        blocked_domains = {
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'yopmail.com', 'throwaway.email'
        }
        
        domain = email_str.split('@')[1] if '@' in email_str else ''
        if domain in blocked_domains:
            raise ValueError('Temporary email addresses are not allowed')
        
        return v

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., 
        min_length=1, 
        max_length=128,
        description="User password"
    )
    
    @validator('email')
    def sanitize_email(cls, v):
        """Sanitize email input"""
        return str(v).lower().strip()
    
    @validator('password')
    def validate_login_password(cls, v):
        """Basic password validation for login"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Password cannot be empty')
        return v

class User(UserBase):
    id: int
    isActive: bool
    createdAt: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    accessToken: str
    tokenType: str = "bearer"