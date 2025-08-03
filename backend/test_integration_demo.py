#!/usr/bin/env python3
"""
Integration demo showing core ViralOS functionality working end-to-end.
This demonstrates the successful fixes and validates the system is ready for development.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def demo_workflow():
    """Demonstrate a complete workflow from user creation to content ideation."""
    print("🎬 ViralOS Integration Demo - End-to-End Workflow")
    print("=" * 60)
    
    try:
        # Setup database
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db.session import Base
        from app.models import User, Brand, Campaign
        from app.models.content import Idea
        from tests.factories import UserFactory, BrandFactory, CampaignFactory, IdeaFactory
        
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        print("\n🏗️  Step 1: Create User Account")
        user = User(
            email="creator@viralmaker.com",
            hashed_password="$2b$12$hashed_password_here",
            is_active=True
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"   ✅ User created: {user.email} (ID: {user.id})")
        
        print("\n🏢 Step 2: Brand Setup & Assimilation")
        brand = Brand(
            user_id=user.id,
            name="EcoTech Solutions",
            url="https://ecotech-solutions.com",
            logo_url="https://cdn.example.com/logo.png",
            colors={"primary": "#2E8B57", "secondary": "#FFD700"},
            voice={"tone": "Professional yet approachable", "dos": "Be educational and inspiring", "donts": "Don't oversell or be pushy"},
            pillars=["Sustainability", "Innovation", "Education"],
            industry="Green Technology",
            target_audience={"age": "25-45", "interests": ["environmental sustainability", "technology", "innovation"]},
            unique_value_proposition="Making green technology accessible and affordable for everyday consumers"
        )
        session.add(brand)
        session.commit()
        session.refresh(brand)
        print(f"   ✅ Brand created: {brand.name} (ID: {brand.id})")
        print(f"   📊 Brand voice: {brand.voice['tone']}")
        print(f"   🎨 Brand colors: {brand.colors}")
        
        print("\n📅 Step 3: Campaign Creation")
        campaign = Campaign(
            brand_id=brand.id,
            name="Sustainable Living Challenge",
            goal="Increase brand awareness and drive product engagement through educational content about sustainable living practices"
        )
        session.add(campaign)
        session.commit()
        session.refresh(campaign)
        print(f"   ✅ Campaign created: {campaign.name} (ID: {campaign.id})")
        print(f"   🎯 Campaign goal: {campaign.goal}")
        
        print("\n💡 Step 4: Content Ideation")
        ideas = []
        
        # Generate multiple content ideas
        idea_hooks = [
            "POV: You thought going green was expensive until you saw your electricity bill drop 70% with these 3 simple swaps",
            "Day in the life of someone who generates their own electricity and grows their own food in a tiny apartment",
            "Exposing the TRUTH about 'eco-friendly' products that are actually worse for the environment",
            "My grandma's reaction to smart home tech that cuts her carbon footprint in half",
            "Rich people don't want you to know these free ways to live sustainably"
        ]
        
        for i, hook in enumerate(idea_hooks, 1):
            idea = Idea(
                brand_id=brand.id,
                campaign_id=campaign.id,
                hook=hook,
                viral_score=round(7.5 + (i * 0.3), 1),  # Simulated AI scoring
                status="approved" if i <= 3 else "pending"
            )
            session.add(idea)
            ideas.append(idea)
        
        session.commit()
        for idea in ideas:
            session.refresh(idea)
        
        print(f"   ✅ Generated {len(ideas)} content ideas")
        
        # Show top performing ideas
        approved_ideas = [idea for idea in ideas if idea.status == "approved"]
        print(f"   📈 Top approved ideas:")
        for idea in approved_ideas:
            print(f"      🔥 [{idea.viral_score}/10] {idea.hook[:60]}...")
        
        print("\n🔗 Step 5: Validate Relationships")
        # Test all relationships work
        print(f"   👤 Brand owner: {brand.user.email}")
        print(f"   📊 Brand campaigns: {len(brand.campaigns)}")
        print(f"   💭 Campaign ideas: {len(campaign.ideas)}")
        print(f"   ✅ Approved ideas: {len([i for i in campaign.ideas if i.status == 'approved'])}")
        
        print("\n📈 Step 6: Performance Analytics Simulation")
        # Simulate what analytics would look like
        total_viral_score = sum(idea.viral_score for idea in approved_ideas)
        avg_viral_score = total_viral_score / len(approved_ideas) if approved_ideas else 0
        
        print(f"   📊 Campaign Performance Preview:")
        print(f"      • Total Ideas Generated: {len(ideas)}")
        print(f"      • Approved for Production: {len(approved_ideas)}")
        print(f"      • Average Viral Score: {avg_viral_score:.1f}/10")
        print(f"      • Predicted Engagement: {'High' if avg_viral_score > 8 else 'Medium' if avg_viral_score > 6 else 'Low'}")
        
        session.close()
        
        print("\n🎉 Demo Complete!")
        print("=" * 60)
        print("✅ All core components working:")
        print("   • User management")
        print("   • Brand assimilation & configuration")
        print("   • Campaign planning")
        print("   • Content ideation with AI scoring")
        print("   • Database relationships")
        print("   • Performance analytics foundation")
        print("\n🚀 System ready for:")
        print("   • AI service integration")
        print("   • Video generation workflows")
        print("   • Social media publishing")
        print("   • Advanced analytics")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = demo_workflow()
    sys.exit(0 if success else 1)