from app.db.session import engine, Base
from app.models import *  # Import all models to ensure they are registered

def init_db():
    """Initialize database tables"""
    # Import all models to ensure they are registered with SQLAlchemy
    from app.models.user import User
    from app.models.brand import Brand, Asset
    from app.models.campaign import Campaign
    from app.models.content import Idea, Blueprint, Video
    from app.models.job import Job
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()