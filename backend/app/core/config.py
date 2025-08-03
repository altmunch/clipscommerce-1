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
    
    # Enhanced Scraping Configuration
    SCRAPING_CONCURRENT_REQUESTS: int = 8
    SCRAPING_DELAY_RANGE: tuple = (1.0, 3.0)
    SCRAPING_MAX_RETRIES: int = 3
    SCRAPING_USE_PROXIES: bool = False
    SCRAPING_PROXY_ROTATION: bool = True
    SCRAPING_RESPECT_ROBOTS: bool = True
    
    # Playwright Configuration
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_TIMEOUT: int = 30000
    PLAYWRIGHT_VIEWPORT_WIDTH: int = 1920
    PLAYWRIGHT_VIEWPORT_HEIGHT: int = 1080
    
    # Anti-Detection
    SCRAPING_RANDOM_USER_AGENTS: bool = True
    SCRAPING_ROTATE_HEADERS: bool = True
    SCRAPING_SIMULATE_HUMAN_BEHAVIOR: bool = True
    
    # Data Quality
    MIN_DATA_QUALITY_SCORE: float = 0.6
    MAX_PRODUCT_NAME_LENGTH: int = 500
    MAX_DESCRIPTION_LENGTH: int = 5000
    
    # Monitoring and Alerts
    SCRAPING_HEALTH_CHECK_INTERVAL: int = 300  # 5 minutes
    SCRAPING_ALERT_COOLDOWN: int = 1800  # 30 minutes
    SCRAPING_MAX_FAILURE_RATE: float = 0.5
    SCRAPING_MAX_RESPONSE_TIME: float = 30.0
    
    # Caching
    CACHE_TTL_EMBEDDINGS: int = 86400  # 24 hours
    CACHE_TTL_ANALYSIS: int = 3600     # 1 hour
    CACHE_TTL_TRENDS: int = 1800       # 30 minutes
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"
    
    # Apify Configuration
    APIFY_API_TOKEN: str = ""
    APIFY_TIKTOK_ACTOR_ID: str = "viralos-tiktok-trend-scraper"
    APIFY_DEFAULT_TIMEOUT: int = 1800  # 30 minutes
    APIFY_MAX_RETRIES: int = 3
    APIFY_RATE_LIMIT_REQUESTS: int = 100
    APIFY_RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Analytics & ML Configuration
    ML_MODELS_DIR: str = "app/ml_models"
    BASE_DIR: str = "/workspaces/api/backend"
    VIDEO_ANALYSIS_TIMEOUT: int = 300  # 5 minutes
    TREND_UPDATE_INTERVAL: int = 3600  # 1 hour
    AB_TEST_MIN_SAMPLE_SIZE: int = 1000
    
    # Social Media API Configuration
    # TikTok Business API
    TIKTOK_APP_ID: str = ""
    TIKTOK_APP_SECRET: str = ""
    TIKTOK_REDIRECT_URI: str = "https://your-domain.com/auth/tiktok/callback"
    TIKTOK_WEBHOOK_SECRET: str = ""
    
    # Instagram/Facebook Graph API
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""
    INSTAGRAM_REDIRECT_URI: str = "https://your-domain.com/auth/instagram/callback"
    INSTAGRAM_WEBHOOK_VERIFY_TOKEN: str = ""
    
    # Social Media Rate Limiting
    SOCIAL_MEDIA_RATE_LIMIT_REQUESTS: int = 100
    SOCIAL_MEDIA_RATE_LIMIT_WINDOW: int = 3600  # 1 hour
    SOCIAL_MEDIA_REQUEST_TIMEOUT: int = 30
    SOCIAL_MEDIA_MAX_RETRIES: int = 3
    
    # Content Upload Settings
    MAX_VIDEO_SIZE_MB: int = 500  # 500MB max video size
    MAX_IMAGE_SIZE_MB: int = 10   # 10MB max image size
    SUPPORTED_VIDEO_FORMATS: List[str] = ["mp4", "mov", "avi"]
    SUPPORTED_IMAGE_FORMATS: List[str] = ["jpg", "jpeg", "png"]
    
    # Posting Strategy Configuration
    DEFAULT_POSTING_STRATEGY: str = "optimized"  # simultaneous, sequential, optimized, a_b_test
    DEFAULT_OPTIMIZATION_MODE: str = "hashtags_only"  # disabled, hashtags_only, caption_only, full_optimization
    AUTO_SCHEDULE_ENABLED: bool = True
    AUTO_HASHTAG_OPTIMIZATION: bool = True
    
    # Analytics Configuration
    ANALYTICS_SYNC_INTERVAL: int = 3600  # 1 hour
    ANALYTICS_RETENTION_DAYS: int = 365  # Keep analytics for 1 year
    WEBHOOK_RETENTION_DAYS: int = 30     # Keep webhook logs for 30 days
    
    # Cross-Platform Posting Settings
    CROSS_PLATFORM_DELAY_SECONDS: int = 30  # Delay between sequential posts
    MAX_SIMULTANEOUS_POSTS: int = 5         # Max platforms to post to simultaneously
    POST_RETRY_ATTEMPTS: int = 3             # Number of retry attempts for failed posts
    
    # Automation Settings
    AUTO_REPLY_ENABLED: bool = False
    AUTO_MODERATION_ENABLED: bool = True
    ENGAGEMENT_THRESHOLD_FOR_PROMOTION: float = 5.0  # Minimum engagement rate for promotion
    
    # Performance Optimization
    ENABLE_CONTENT_CACHING: bool = True
    CACHE_TTL_SOCIAL_MEDIA: int = 1800  # 30 minutes
    ENABLE_ASYNC_POSTING: bool = True
    BATCH_ANALYTICS_SYNC: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()