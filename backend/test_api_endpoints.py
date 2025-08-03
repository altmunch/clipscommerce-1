#!/usr/bin/env python3
"""
Test script to validate FastAPI endpoints functionality
"""

import asyncio
import sys
from typing import Dict, List, Any
from fastapi.testclient import TestClient
import json

def test_app_creation():
    """Test that the FastAPI app can be created"""
    try:
        from app.main import app
        return "OK - FastAPI app created successfully"
    except Exception as e:
        return f"FAIL - App creation error: {e}"

def test_basic_endpoints():
    """Test basic endpoints without authentication"""
    try:
        from app.main import app
        client = TestClient(app)
        
        results = {}
        
        # Test root endpoint
        try:
            response = client.get("/")
            results['root'] = f"OK - Status: {response.status_code}"
        except Exception as e:
            results['root'] = f"FAIL: {e}"
        
        # Test health endpoint
        try:
            response = client.get("/health")
            results['health'] = f"OK - Status: {response.status_code}"
        except Exception as e:
            results['health'] = f"FAIL: {e}"
        
        # Test OpenAPI docs
        try:
            response = client.get("/api/v1/openapi.json")
            results['openapi'] = f"OK - Status: {response.status_code}"
        except Exception as e:
            results['openapi'] = f"FAIL: {e}"
        
        return results
    except Exception as e:
        return f"FAIL - Client creation error: {e}"

def test_endpoint_routes():
    """Test that all endpoint routes are properly registered"""
    try:
        from app.main import app
        client = TestClient(app)
        
        results = {}
        
        # Get OpenAPI schema to check registered routes
        response = client.get("/api/v1/openapi.json")
        if response.status_code == 200:
            openapi_data = response.json()
            paths = openapi_data.get("paths", {})
            
            # Check for main endpoint groups
            endpoint_groups = [
                "/api/v1/auth",
                "/api/v1/brands", 
                "/api/v1/campaigns",
                "/api/v1/results",
                "/api/v1/jobs",
                "/api/v1/scraping",
                "/api/v1/tiktok",
                "/api/v1/video",
                "/api/v1/analytics",
                "/api/v1/social-media"
            ]
            
            for group in endpoint_groups:
                # Check if any paths start with this group
                group_paths = [path for path in paths.keys() if path.startswith(group)]
                if group_paths:
                    results[group] = f"OK - {len(group_paths)} endpoints"
                else:
                    results[group] = "MISSING - No endpoints found"
            
            results['total_paths'] = f"OK - {len(paths)} total endpoints"
        else:
            results['openapi_fetch'] = f"FAIL - Could not fetch OpenAPI schema: {response.status_code}"
        
        return results
    except Exception as e:
        return f"FAIL - Route testing error: {e}"

def test_endpoint_access():
    """Test actual endpoint access (should return proper status codes)"""
    try:
        from app.main import app
        client = TestClient(app)
        
        results = {}
        
        # Test endpoints that should be accessible without auth
        test_endpoints = [
            ("GET", "/api/v1/brands", "List brands"),
            ("GET", "/api/v1/campaigns", "List campaigns"),
            ("GET", "/api/v1/jobs", "List jobs"),
            ("GET", "/api/v1/scraping/health", "Scraping health check"),
            ("GET", "/api/v1/tiktok/health", "TikTok health check"),
            ("GET", "/api/v1/analytics/health", "Analytics health check"),
        ]
        
        for method, endpoint, description in test_endpoints:
            try:
                if method == "GET":
                    response = client.get(endpoint)
                else:
                    response = client.request(method, endpoint)
                
                # Accept 200 (OK), 401 (Unauthorized), 422 (Validation Error) as expected
                if response.status_code in [200, 401, 422]:
                    results[endpoint] = f"OK - {response.status_code}"
                else:
                    results[endpoint] = f"UNEXPECTED - {response.status_code}"
                    
            except Exception as e:
                results[endpoint] = f"ERROR: {e}"
        
        return results
    except Exception as e:
        return f"FAIL - Endpoint access error: {e}"

def test_request_validation():
    """Test request validation for POST endpoints"""
    try:
        from app.main import app
        client = TestClient(app)
        
        results = {}
        
        # Test POST endpoints with invalid data to check validation
        test_posts = [
            ("/api/v1/brands/", {}, "Create brand with empty data"),
            ("/api/v1/campaigns/", {}, "Create campaign with empty data"),
            ("/api/v1/video/generate", {}, "Generate video with empty data"),
        ]
        
        for endpoint, data, description in test_posts:
            try:
                response = client.post(endpoint, json=data)
                
                # Should return 422 (validation error) or 401 (unauthorized)
                if response.status_code in [422, 401]:
                    results[endpoint] = f"OK - {response.status_code} (validation working)"
                else:
                    results[endpoint] = f"UNEXPECTED - {response.status_code}"
                    
            except Exception as e:
                results[endpoint] = f"ERROR: {e}"
        
        return results
    except Exception as e:
        return f"FAIL - Validation testing error: {e}"

def test_cors_middleware():
    """Test CORS middleware configuration"""
    try:
        from app.main import app
        client = TestClient(app)
        
        # Test CORS preflight request
        response = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type"
        })
        
        cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods", 
            "Access-Control-Allow-Headers"
        ]
        
        present_headers = [h for h in cors_headers if h in response.headers]
        
        if len(present_headers) > 0:
            return f"OK - CORS headers present: {present_headers}"
        else:
            return "WARNING - No CORS headers found"
            
    except Exception as e:
        return f"FAIL - CORS testing error: {e}"

def test_exception_handling():
    """Test custom exception handling"""
    try:
        from app.main import app
        client = TestClient(app)
        
        # Test non-existent endpoint (should return 404)
        response = client.get("/api/v1/nonexistent")
        
        if response.status_code == 404:
            return "OK - 404 handling works"
        else:
            return f"UNEXPECTED - Got {response.status_code} instead of 404"
            
    except Exception as e:
        return f"FAIL - Exception handling error: {e}"

def main():
    print("=== ViralOS FastAPI Endpoints Test ===\n")
    
    print("1. Testing FastAPI app creation...")
    app_result = test_app_creation()
    print(f"   App creation: {app_result}")
    
    if "FAIL" in app_result:
        print("\nCannot proceed with endpoint tests due to app creation failure.")
        return 1
    
    print("\n2. Testing basic endpoints...")
    basic_results = test_basic_endpoints()
    if isinstance(basic_results, dict):
        for endpoint, status in basic_results.items():
            print(f"   {endpoint}: {status}")
    else:
        print(f"   {basic_results}")
    
    print("\n3. Testing endpoint route registration...")
    route_results = test_endpoint_routes()
    if isinstance(route_results, dict):
        for group, status in route_results.items():
            print(f"   {group}: {status}")
    else:
        print(f"   {route_results}")
    
    print("\n4. Testing endpoint access...")
    access_results = test_endpoint_access()
    if isinstance(access_results, dict):
        for endpoint, status in access_results.items():
            print(f"   {endpoint}: {status}")
    else:
        print(f"   {access_results}")
    
    print("\n5. Testing request validation...")
    validation_results = test_request_validation()
    if isinstance(validation_results, dict):
        for endpoint, status in validation_results.items():
            print(f"   {endpoint}: {status}")
    else:
        print(f"   {validation_results}")
    
    print("\n6. Testing CORS middleware...")
    cors_result = test_cors_middleware()
    print(f"   CORS: {cors_result}")
    
    print("\n7. Testing exception handling...")
    exception_result = test_exception_handling()
    print(f"   Exception handling: {exception_result}")
    
    print("\n=== Test Complete ===")
    
    # Summary
    all_results = {}
    all_results['app_creation'] = app_result
    if isinstance(basic_results, dict):
        all_results.update(basic_results)
    if isinstance(route_results, dict):
        all_results.update(route_results)
    if isinstance(access_results, dict):
        all_results.update(access_results)
    if isinstance(validation_results, dict):
        all_results.update(validation_results)
    all_results['cors'] = cors_result
    all_results['exception_handling'] = exception_result
    
    failed_count = sum(1 for status in all_results.values() if isinstance(status, str) and 'FAIL' in status)
    error_count = sum(1 for status in all_results.values() if isinstance(status, str) and 'ERROR' in status)
    warning_count = sum(1 for status in all_results.values() if isinstance(status, str) and 'WARNING' in status)
    total_count = len(all_results)
    
    passed_count = total_count - failed_count - error_count
    
    print(f"\nSummary: {passed_count}/{total_count} tests passed")
    
    if failed_count > 0:
        print(f"Failed tests: {failed_count}")
    if error_count > 0:
        print(f"Tests with errors: {error_count}")
    if warning_count > 0:
        print(f"Tests with warnings: {warning_count}")
    
    return 1 if failed_count > 0 else 0

if __name__ == "__main__":
    sys.exit(main())