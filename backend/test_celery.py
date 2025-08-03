#!/usr/bin/env python3
"""
Test script to validate Celery worker connectivity and task execution
"""

import os
import sys
import time
import asyncio
from typing import Dict, Any
import redis

def test_redis_connection():
    """Test Redis connectivity"""
    try:
        from app.core.config import settings
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        return "OK - Redis is accessible"
    except Exception as e:
        return f"FAIL - Redis connection error: {e}"

def test_celery_configuration():
    """Test Celery app configuration"""
    try:
        from app.core.celery_app import celery_app
        
        results = {}
        results['broker_url'] = celery_app.conf.broker_url
        results['result_backend'] = celery_app.conf.result_backend
        results['task_serializer'] = celery_app.conf.task_serializer
        results['timezone'] = celery_app.conf.timezone
        
        return results
    except Exception as e:
        return f"FAIL - Celery configuration error: {e}"

def test_task_imports():
    """Test that all Celery tasks can be imported"""
    results = {}
    
    task_modules = [
        'app.tasks.brand_tasks',
        'app.tasks.content_tasks', 
        'app.tasks.scraping_tasks',
        'app.tasks.video_generation_tasks',
        'app.tasks.social_media_tasks',
        'app.tasks.analytics_tasks',
        'app.tasks.tiktok_tasks'
    ]
    
    for module in task_modules:
        try:
            __import__(module)
            results[module] = "OK"
        except Exception as e:
            results[module] = f"FAIL: {e}"
    
    return results

def test_celery_tasks():
    """Test basic Celery task functionality (without worker)"""
    try:
        from app.core.celery_app import celery_app
        
        # Test simple task definition
        @celery_app.task
        def test_task(x, y):
            return x + y
        
        # Check if task is registered
        task_name = test_task.name
        if task_name in celery_app.tasks:
            return f"OK - Task registered as {task_name}"
        else:
            return "FAIL - Task not registered"
            
    except Exception as e:
        return f"FAIL - Task creation error: {e}"

def test_celery_inspect():
    """Test Celery inspection capabilities"""
    try:
        from app.core.celery_app import celery_app
        inspect = celery_app.control.inspect()
        
        results = {}
        
        # Check active workers (will be empty if no workers running)
        try:
            active = inspect.active()
            results['active_workers'] = len(active) if active else 0
        except Exception as e:
            results['active_workers'] = f"Error: {e}"
        
        # Check registered tasks
        try:
            registered = inspect.registered()
            results['registered_tasks'] = len(registered) if registered else 0
        except Exception as e:
            results['registered_tasks'] = f"Error: {e}"
        
        # Check stats (will fail if no workers)
        try:
            stats = inspect.stats()
            results['worker_stats'] = len(stats) if stats else 0
        except Exception as e:
            results['worker_stats'] = f"Error: {e}"
        
        return results
    except Exception as e:
        return f"FAIL - Celery inspect error: {e}"

def test_specific_tasks():
    """Test specific ViralOS tasks exist and are properly configured"""
    results = {}
    
    try:
        from app.tasks.brand_tasks import assimilate_brand
        results['assimilate_brand'] = f"OK - {assimilate_brand.name}"
    except Exception as e:
        results['assimilate_brand'] = f"FAIL: {e}"
    
    try:
        from app.tasks.content_tasks import generate_video
        results['content_generate_video'] = f"OK - {generate_video.name}"
    except Exception as e:
        results['content_generate_video'] = f"FAIL: {e}"
    
    try:
        from app.tasks.video_generation_tasks import generate_video_task
        results['video_generation_task'] = f"OK - {generate_video_task.name}"
    except Exception as e:
        results['video_generation_task'] = f"FAIL: {e}"
    
    try:
        from app.tasks.social_media_tasks import process_scheduled_posts
        results['process_scheduled_posts'] = f"OK - {process_scheduled_posts.name}"
    except Exception as e:
        results['process_scheduled_posts'] = f"FAIL: {e}"
    
    return results

def main():
    print("=== ViralOS Celery Test ===\n")
    
    print("1. Testing Redis connection...")
    redis_result = test_redis_connection()
    print(f"   Redis: {redis_result}")
    
    print("\n2. Testing Celery configuration...")
    celery_config = test_celery_configuration()
    if isinstance(celery_config, dict):
        for key, value in celery_config.items():
            print(f"   {key}: {value}")
    else:
        print(f"   {celery_config}")
    
    print("\n3. Testing task module imports...")
    import_results = test_task_imports()
    for module, status in import_results.items():
        print(f"   {module}: {status}")
    
    print("\n4. Testing basic Celery task functionality...")
    task_result = test_celery_tasks()
    print(f"   Task creation: {task_result}")
    
    print("\n5. Testing Celery inspection...")
    inspect_results = test_celery_inspect()
    if isinstance(inspect_results, dict):
        for key, value in inspect_results.items():
            print(f"   {key}: {value}")
    else:
        print(f"   {inspect_results}")
    
    print("\n6. Testing specific ViralOS tasks...")
    specific_results = test_specific_tasks()
    for task, status in specific_results.items():
        print(f"   {task}: {status}")
    
    print("\n=== Test Complete ===")
    
    # Summary
    all_results = {}
    all_results['redis'] = redis_result
    if isinstance(celery_config, dict):
        all_results.update(celery_config)
    all_results.update(import_results)
    all_results['task_creation'] = task_result
    if isinstance(inspect_results, dict):
        all_results.update(inspect_results)
    all_results.update(specific_results)
    
    failed_count = sum(1 for status in all_results.values() if isinstance(status, str) and 'FAIL' in status)
    error_count = sum(1 for status in all_results.values() if isinstance(status, str) and 'Error' in status)
    total_count = len(all_results)
    
    print(f"\nSummary: {total_count - failed_count - error_count}/{total_count} tests passed")
    
    if failed_count > 0:
        print(f"Failed tests: {failed_count}")
    if error_count > 0:
        print(f"Tests with errors (likely due to no running workers): {error_count}")
    
    # Note about workers
    if error_count > 0:
        print("\nNote: Some errors are expected when no Celery workers are running.")
        print("To start a worker, run: celery -A app.core.celery_app worker --loglevel=info")
    
    return 1 if failed_count > 0 else 0

if __name__ == "__main__":
    sys.exit(main())