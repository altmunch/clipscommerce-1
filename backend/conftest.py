import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.config import settings
from app.db.session import get_db
from app.models import Base
from tests.factories import UserFactory, BrandFactory, CampaignFactory, ContentFactory

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def override_get_db(db_session):
    """Override the get_db dependency to use test database."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(override_get_db):
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_openai_client(mocker):
    """Mock OpenAI client for testing AI services."""
    mock_client = mocker.Mock()
    
    # Mock chat completions
    mock_client.chat.completions.create.return_value = mocker.Mock(
        choices=[
            mocker.Mock(
                message=mocker.Mock(
                    content='{"result": "mocked response"}'
                )
            )
        ]
    )
    
    # Mock embeddings
    mock_client.embeddings.create.return_value = mocker.Mock(
        data=[
            mocker.Mock(embedding=[0.1, 0.2, 0.3])
        ]
    )
    
    return mock_client


@pytest.fixture
def mock_anthropic_client(mocker):
    """Mock Anthropic client for testing AI services."""
    mock_client = mocker.Mock()
    
    mock_client.messages.create.return_value = mocker.Mock(
        content=[
            mocker.Mock(text='{"result": "mocked anthropic response"}')
        ]
    )
    
    return mock_client


@pytest.fixture
def mock_celery(mocker):
    """Mock Celery for testing async tasks."""
    mock_task = mocker.Mock()
    mock_task.delay.return_value = mocker.Mock(
        id="mock-task-id",
        status="SUCCESS",
        result={"message": "Task completed"}
    )
    return mock_task


@pytest.fixture
def mock_redis(mocker):
    """Mock Redis for testing caching."""
    mock_redis = mocker.Mock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    return mock_redis


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = UserFactory.create()
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_brand(db_session, sample_user):
    """Create a sample brand for testing."""
    brand = BrandFactory.create(user_id=sample_user.id)
    db_session.add(brand)
    db_session.commit()
    db_session.refresh(brand)
    return brand


@pytest.fixture
def sample_campaign(db_session, sample_brand):
    """Create a sample campaign for testing."""
    campaign = CampaignFactory.create(brand_id=sample_brand.id)
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)
    return campaign


@pytest.fixture
def sample_content(db_session, sample_brand, sample_campaign):
    """Create a sample content for testing."""
    content = ContentFactory.create(
        brand_id=sample_brand.id,
        campaign_id=sample_campaign.id
    )
    db_session.add(content)
    db_session.commit()
    db_session.refresh(content)
    return content


@pytest.fixture
def auth_headers(sample_user):
    """Create authentication headers for testing."""
    # In a real app, you'd generate a JWT token here
    return {"Authorization": f"Bearer mock-jwt-token-{sample_user.id}"}


@pytest.fixture(autouse=True)
def mock_external_services(mocker):
    """Auto-mock external services to prevent real API calls during tests."""
    # Mock HTTP requests
    mocker.patch('httpx.AsyncClient.get')
    mocker.patch('httpx.AsyncClient.post')
    mocker.patch('httpx.AsyncClient.put')
    mocker.patch('httpx.AsyncClient.delete')
    
    # Mock vector databases
    mocker.patch('pinecone.Index')
    mocker.patch('weaviate.Client')
    
    # Mock file operations
    mocker.patch('builtins.open', mocker.mock_open())
    
    # Mock external AI APIs
    mocker.patch('openai.OpenAI')
    mocker.patch('anthropic.Anthropic')


@pytest.fixture
def mock_vector_db(mocker):
    """Mock vector database operations."""
    mock_db = mocker.Mock()
    mock_db.upsert.return_value = {"upserted_count": 1}
    mock_db.query.return_value = {
        "matches": [
            {
                "id": "mock-id",
                "score": 0.95,
                "metadata": {"text": "mock content"}
            }
        ]
    }
    return mock_db


@pytest.fixture
def mock_file_storage(mocker, tmp_path):
    """Mock file storage operations."""
    storage_path = tmp_path / "storage"
    storage_path.mkdir()
    
    mock_storage = mocker.Mock()
    mock_storage.upload.return_value = f"{storage_path}/mock-file.jpg"
    mock_storage.download.return_value = b"mock file content"
    mock_storage.delete.return_value = True
    
    return mock_storage


# Pytest markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.ai = pytest.mark.ai
pytest.mark.celery = pytest.mark.celery
pytest.mark.db = pytest.mark.db