#!/usr/bin/env python3
"""
Test script to validate AI service integrations
"""

import os
import sys
import asyncio
from typing import Dict, Any

def test_basic_imports():
    """Test basic import of AI libraries"""
    results = {}
    
    # Test core AI libraries
    try:
        import openai
        results['openai'] = 'OK'
    except Exception as e:
        results['openai'] = f'FAIL: {e}'
    
    try:
        import anthropic
        results['anthropic'] = 'OK'
    except Exception as e:
        results['anthropic'] = f'FAIL: {e}'
    
    try:
        import elevenlabs
        results['elevenlabs'] = 'OK'
    except Exception as e:
        results['elevenlabs'] = f'FAIL: {e}'
    
    try:
        import runwayml
        results['runwayml'] = 'OK'
    except Exception as e:
        results['runwayml'] = f'FAIL: {e}'
    
    try:
        import replicate
        results['replicate'] = 'OK'
    except Exception as e:
        results['replicate'] = f'FAIL: {e}'
    
    try:
        import pinecone
        results['pinecone'] = 'OK'
    except Exception as e:
        results['pinecone'] = f'FAIL: {e}'
    
    try:
        import weaviate
        results['weaviate'] = 'OK'
    except Exception as e:
        results['weaviate'] = f'FAIL: {e}'
    
    return results

async def test_ai_services():
    """Test ViralOS AI service classes"""
    results = {}
    
    try:
        from app.services.ai.providers import get_text_service, get_embedding_service
        results['ai_providers'] = 'OK'
    except Exception as e:
        results['ai_providers'] = f'FAIL: {e}'
        return results
    
    try:
        from app.services.video_generation.providers import RunwayMLProvider
        results['video_providers'] = 'OK'
    except Exception as e:
        results['video_providers'] = f'FAIL: {e}'
    
    try:
        from app.services.video_generation.text_to_speech import get_tts_service
        results['tts_service'] = 'OK'
    except Exception as e:
        results['tts_service'] = f'FAIL: {e}'
    
    try:
        from app.services.analytics.performance_predictor import PerformancePredictor
        results['performance_predictor'] = 'OK'
    except Exception as e:
        results['performance_predictor'] = f'FAIL: {e}'
    
    try:
        from app.services.analytics.trend_engine import TrendRecommendationEngine
        results['trend_engine'] = 'OK'
    except Exception as e:
        results['trend_engine'] = f'FAIL: {e}'
    
    return results

def test_configuration():
    """Test AI service configuration"""
    results = {}
    
    try:
        from app.core.config import settings
        
        # Check if API keys are configured (but don't print them)
        results['openai_configured'] = 'YES' if settings.OPENAI_API_KEY else 'NO'
        results['anthropic_configured'] = 'YES' if settings.ANTHROPIC_API_KEY else 'NO'
        results['pinecone_configured'] = 'YES' if settings.PINECONE_API_KEY else 'NO'
        results['weaviate_configured'] = 'YES' if settings.WEAVIATE_URL else 'NO'
        
    except Exception as e:
        results['config_error'] = f'FAIL: {e}'
    
    return results

def main():
    print("=== ViralOS AI Services Test ===\n")
    
    print("1. Testing basic AI library imports...")
    import_results = test_basic_imports()
    for lib, status in import_results.items():
        print(f"   {lib}: {status}")
    
    print("\n2. Testing ViralOS AI service classes...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        service_results = loop.run_until_complete(test_ai_services())
        for service, status in service_results.items():
            print(f"   {service}: {status}")
    finally:
        loop.close()
    
    print("\n3. Testing configuration...")
    config_results = test_configuration()
    for config, status in config_results.items():
        print(f"   {config}: {status}")
    
    print("\n=== Test Complete ===")
    
    # Summary
    all_results = {**import_results, **service_results, **config_results}
    failed_count = sum(1 for status in all_results.values() if 'FAIL' in status)
    total_count = len(all_results)
    
    print(f"\nSummary: {total_count - failed_count}/{total_count} tests passed")
    
    if failed_count > 0:
        print(f"Failed tests: {failed_count}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())