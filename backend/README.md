# ViralOS Backend API

AI-Powered Video Marketing Platform Backend built with FastAPI, PostgreSQL, Redis, and Celery.

## Features

- **Authentication**: JWT-based user authentication and authorization
- **Brand Management**: Brand assimilation from URLs with AI-powered analysis
- **Campaign Management**: Strategic campaign creation and management
- **Content Pipeline**: AI-powered content ideation, blueprint generation, and video creation
- **Results Analytics**: Performance tracking and insights
- **Async Processing**: Background job processing with Celery and Redis
- **Production Ready**: Proper error handling, logging, and Docker support

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Background Jobs**: Celery with Redis
- **Authentication**: JWT tokens with passlib
- **Migrations**: Alembic
- **Containerization**: Docker and Docker Compose

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login

### Brands
- `POST /api/v1/brands/assimilate` - Start brand assimilation (async)
- `GET /api/v1/brands` - Get user's brands
- `GET /api/v1/brands/{brandId}/kit` - Get brand kit
- `PUT /api/v1/brands/{brandId}/kit` - Update brand kit

### Campaigns
- `POST /api/v1/campaigns` - Create campaign
- `GET /api/v1/campaigns?brandId={brandId}` - Get campaigns

### Content Pipeline
- `POST /api/v1/ideas/generate` - Generate content ideas (async)
- `GET /api/v1/ideas?brandId={brandId}` - Get generated ideas
- `POST /api/v1/blueprints/generate` - Generate blueprint (async)
- `POST /api/v1/videos/generate-ai` - Generate AI video (async)
- `PUT /api/v1/videos/{videoId}/optimize` - Optimize video
- `POST /api/v1/videos/{videoId}/schedule` - Schedule video

### Results
- `GET /api/v1/results/kpis` - Get KPI data
- `GET /api/v1/results/chart` - Get chart data
- `GET /api/v1/results/content` - Get content performance
- `GET /api/v1/results/insights` - Get AI insights

### Jobs
- `GET /api/v1/jobs/{jobId}/status` - Get job status

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to backend directory**
   ```bash
   cd /workspaces/api/backend
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

4. **Run migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **API will be available at**: http://localhost:8000
   **API Documentation**: http://localhost:8000/docs

### Manual Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start PostgreSQL and Redis**
   ```bash
   # Using Docker
   docker run -d --name postgres -e POSTGRES_DB=viralos -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15
   docker run -d --name redis -p 6379:6379 redis:7-alpine
   ```

4. **Run migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the application**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Start Celery worker (in another terminal)**
   ```bash
   celery -A app.core.celery_app worker --loglevel=info
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:password@localhost:5432/viralos` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `SECRET_KEY` | JWT secret key | Auto-generated |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time | `11520` (8 days) |
| `BACKEND_CORS_ORIGINS` | Allowed CORS origins | `[]` |
| `OPENAI_API_KEY` | OpenAI API key | Required for AI features |
| `AWS_ACCESS_KEY_ID` | AWS access key | Required for S3 storage |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required for S3 storage |
| `AWS_S3_BUCKET` | S3 bucket name | Required for file storage |

## Architecture

### Database Schema

- **Users**: User accounts and authentication
- **Brands**: Brand information and settings
- **Assets**: Brand assets (logos, images, etc.)
- **Campaigns**: Marketing campaigns
- **Ideas**: Generated content ideas
- **Blueprints**: Detailed content scripts and shot lists
- **Videos**: Generated videos with performance metrics
- **Jobs**: Background job tracking

### Background Jobs

- **Brand Assimilation**: Web scraping and brand analysis
- **Idea Generation**: AI-powered content ideation
- **Blueprint Generation**: Script and shot list creation
- **Video Generation**: AI video creation

### Services

- **BrandService**: Brand management business logic
- **Authentication**: JWT token management
- **Exception Handling**: Custom error handling and logging

## Development

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## Production Deployment

### Docker
```bash
# Build image
docker build -t viralos-backend .

# Run container
docker run -d -p 8000:8000 --env-file .env viralos-backend
```

### AWS ECS / Google Cloud Run
The application is configured for containerized deployment on cloud platforms.

## Contributing

1. Follow PEP 8 style guidelines
2. Add proper error handling and logging
3. Write tests for new features
4. Update API documentation
5. Use proper commit messages

## License

Proprietary - ViralOS Platform