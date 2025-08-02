from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings
import secrets

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/viralos"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # AI Services
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # Vector Databases
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = ""
    PINECONE_INDEX_NAME: str = "viralos-content"
    
    WEAVIATE_URL: str = ""
    WEAVIATE_API_KEY: str = ""
    
    # AI Configuration
    DEFAULT_MODEL_PROVIDER: str = "openai"  # openai, anthropic
    DEFAULT_TEXT_MODEL: str = "gpt-4-turbo"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"
    MAX_TOKENS_PER_REQUEST: int = 4000
    AI_REQUEST_TIMEOUT: int = 60
    AI_MAX_RETRIES: int = 3
    
    # Content Generation Settings
    VIRAL_SCORE_THRESHOLD: float = 7.0
    MAX_HOOK_VARIATIONS: int = 5
    MAX_SCRIPT_LENGTH: int = 1000
    
    # Web Scraping
    USER_AGENT: str = "ViralOS/1.0 (+https://viralos.com)"
    SCRAPING_TIMEOUT: int = 30
    MAX_PAGES_PER_DOMAIN: int = 10
    
    # Caching
    CACHE_TTL_EMBEDDINGS: int = 86400  # 24 hours
    CACHE_TTL_ANALYSIS: int = 3600     # 1 hour
    CACHE_TTL_TRENDS: int = 1800       # 30 minutes
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()