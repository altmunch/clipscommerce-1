#!/usr/bin/env python3
"""
Basic functionality test script to validate core ViralOS components.
This script tests the most critical parts of the system to identify issues.
"""

import sys
import traceback
from datetime import datetime
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test basic imports."""
    print("🔍 Testing basic imports...")
    
    try:
        print("  ✓ Testing core configuration...")
        from app.core.config import settings
        print(f"    Database URL configured: {bool(settings.DATABASE_URL)}")
        
        print("  ✓ Testing model imports...")
        from app.models import User, Brand, Campaign
        from app.models.content import Idea, Blueprint, Video
        
        print("  ✓ Testing factory imports...")
        from tests.factories import UserFactory, BrandFactory, IdeaFactory
        
        print("  ✓ Testing service imports...")
        # Test only core services that don't require external connections
        from app.services.ai.base import BaseAIService
        
        print("✅ All core imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False

def test_factories():
    """Test data factory functionality."""
    print("\n🔍 Testing data factories...")
    
    try:
        from tests.factories import UserFactory, BrandFactory, IdeaFactory
        
        print("  ✓ Testing UserFactory...")
        user = UserFactory.build()
        assert user.email
        assert user.hashed_password
        print(f"    Generated user: {user.email}")
        
        print("  ✓ Testing BrandFactory...")
        brand = BrandFactory.build()
        assert brand.name
        assert brand.url
        print(f"    Generated brand: {brand.name}")
        
        print("  ✓ Testing IdeaFactory...")
        idea = IdeaFactory.build()
        assert idea.hook
        assert idea.viral_score is not None
        print(f"    Generated idea: {idea.hook[:50]}...")
        
        print("✅ All factories working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Factory test failed: {e}")
        traceback.print_exc()
        return False

def test_database_models():
    """Test SQLAlchemy model creation with SQLite."""
    print("\n🔍 Testing database models...")
    
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db.session import Base
        from app.models import User, Brand, Campaign
        
        # Create in-memory SQLite database
        engine = create_engine("sqlite:///:memory:", echo=False)
        
        print("  ✓ Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        print("  ✓ Creating database session...")
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        print("  ✓ Testing User model...")
        user = User(
            email="test@example.com",
            hashed_password="hashed_password_123",
            is_active=True
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"    Created user with ID: {user.id}")
        
        print("  ✓ Testing Brand model...")
        brand = Brand(
            user_id=user.id,
            name="Test Brand",
            url="https://testbrand.com"
        )
        session.add(brand)
        session.commit()
        session.refresh(brand)
        print(f"    Created brand with ID: {brand.id}")
        
        print("  ✓ Testing Campaign model...")
        campaign = Campaign(
            brand_id=brand.id,
            name="Test Campaign",
            goal="Increase brand awareness"
        )
        session.add(campaign)
        session.commit()
        session.refresh(campaign)
        print(f"    Created campaign with ID: {campaign.id}")
        
        # Test relationships
        print("  ✓ Testing model relationships...")
        assert brand.user.email == "test@example.com"
        assert len(brand.campaigns) == 1
        assert campaign.brand.name == "Test Brand"
        
        session.close()
        print("✅ Database models working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Database model test failed: {e}")
        traceback.print_exc()
        return False

def test_api_schemas():
    """Test Pydantic schemas."""
    print("\n🔍 Testing API schemas...")
    
    try:
        from app.schemas.user import UserCreate, User as UserSchema
        from app.schemas.brand import BrandCreate, Brand as BrandSchema
        
        print("  ✓ Testing UserCreate schema...")
        user_data = {
            "email": "test@example.com",
            "password": "securepassword123"
        }
        user_create = UserCreate(**user_data)
        assert user_create.email == "test@example.com"
        
        print("  ✓ Testing BrandCreate schema...")
        brand_data = {
            "name": "Test Brand",
            "url": "https://testbrand.com"
        }
        brand_create = BrandCreate(**brand_data)
        assert brand_create.name == "Test Brand"
        
        print("✅ API schemas working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ API schema test failed: {e}")
        traceback.print_exc()
        return False

def test_basic_api_structure():
    """Test that FastAPI app can be created."""
    print("\n🔍 Testing basic API structure...")
    
    try:
        # Import with error handling to avoid dependency issues
        try:
            from app.main import app
            print("  ✓ FastAPI app imported successfully")
        except ImportError as e:
            print(f"  ⚠️  FastAPI app import failed (dependency issue): {e}")
            return False
        
        # Test basic app properties
        assert app is not None
        print(f"  ✓ App title: {getattr(app, 'title', 'N/A')}")
        
        # Test that basic routes exist
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        print(f"  ✓ Found {len(routes)} routes")
        
        print("✅ Basic API structure working!")
        return True
        
    except Exception as e:
        print(f"❌ API structure test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all basic functionality tests."""
    print("🚀 Starting ViralOS Basic Functionality Tests")
    print("=" * 60)
    
    test_results = {
        "imports": test_imports(),
        "factories": test_factories(),
        "database_models": test_database_models(),
        "api_schemas": test_api_schemas(),
        "api_structure": test_basic_api_structure()
    }
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title():<20}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All basic functionality tests passed!")
        print("The ViralOS core components are working correctly.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("Please check the error messages above and fix the issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)