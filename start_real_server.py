#!/usr/bin/env python3
"""
Start script for real ClipsCommerce backend services
Bypasses complex dependencies while using real AI services
"""

import os
import sys

# Add the backend directory to Python path
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

# Load environment variables from .env file
def load_env_file():
    env_path = os.path.join(backend_dir, '.env')
    if os.path.exists(env_path):
        print(f"📄 Loading environment variables from {env_path}")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())
        
        # Check if we have required API keys
        openai_key = os.environ.get('OPENAI_API_KEY', '')
        deepseek_key = os.environ.get('DEEPSEEK_API_KEY', '')
        
        if openai_key and openai_key != 'your-openai-api-key':
            print("✅ OpenAI API key loaded")
        else:
            print("⚠️  OpenAI API key missing - AI features will fail")
            
        if deepseek_key and deepseek_key != 'your-deepseek-api-key':
            print("✅ DeepSeek API key loaded")
        else:
            print("⚠️  DeepSeek API key missing")
    else:
        print(f"⚠️  No .env file found at {env_path}")

load_env_file()

# Set minimal fallback environment variables
os.environ.setdefault('API_V1_STR', '/api/v1')
os.environ.setdefault('BACKEND_CORS_ORIGINS', 'http://localhost:3000,http://localhost:8000')

# Try to import and run the minimal server
try:
    from backend.minimal_main import app
    import uvicorn
    
    print("""
🚀 Starting ClipsCommerce with REAL Backend Services

🔥 Real Services Loaded:
   ✅ CoreBrandScraper - Real web scraping
   ✅ ViralContentGenerator - Real AI content generation  
   ✅ ProductionGuideGenerator - Real production guides
   ✅ SEOOptimizer - Real SEO optimization

🌐 Access Points:
   • API Server: http://localhost:8000
   • Test Interface: http://localhost:8000/test
   • Health Check: http://localhost:8000/health  
   • API Documentation: http://localhost:8000/docs

💡 Test with a real brand URL like:
   • skincare brand: https://theordinary.com
   • tech brand: https://apple.com
   • fashion brand: https://nike.com

Press Ctrl+C to stop the server
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
    
except ImportError as e:
    print(f"""
❌ Import Error: {e}

📦 Installing required packages...
""")
    
    # Try to install minimal requirements
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "backend/minimal_requirements.txt"])
        print("✅ Packages installed! Please run the script again.")
    except:
        print("""
❌ Could not install packages. Please install manually:

pip install fastapi uvicorn pydantic aiohttp beautifulsoup4 selectolax diskcache numpy

Then run this script again.
        """)

except Exception as e:
    print(f"""
❌ Error starting server: {e}

🔧 This might happen if:
   1. Missing dependencies (run: pip install -r backend/minimal_requirements.txt)
   2. Missing environment variables (OpenAI API key, etc.)
   3. Import path issues

💡 Try running from the project root directory.
    """)