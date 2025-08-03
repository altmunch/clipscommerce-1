"""
Simple configuration for minimal backend
"""

import os

class Settings:
    # API Configuration
    API_V1_STR = "/api/v1"
    
    # AI Service Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    # Cache Configuration
    CACHE_TTL_TRENDS = 3600
    CACHE_TTL_BRAND_DATA = 7200
    
    # CORS
    BACKEND_CORS_ORIGINS = ["*"]

settings = Settings()