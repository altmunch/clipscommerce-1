"""
Locust load testing configuration for ViralOS API.
Run with: locust -f locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, SequentialTaskSet
import json
import random
from typing import Dict, Any


class BrandWorkflowTaskSet(SequentialTaskSet):
    """Sequential tasks representing a complete brand workflow."""
    
    def on_start(self):
        """Initialize workflow data."""
        self.brand_id = f"brand-{random.randint(1, 1000)}"
        self.campaign_id = None
        self.video_project_id = None
        self.job_ids = []
    
    @task
    def step_1_analyze_brand(self):
        """Step 1: Analyze brand URL."""
        data = {
            "url": f"https://example-brand-{random.randint(1, 100)}.com"
        }
        
        with self.client.post(f"/api/v1/brands/{self.brand_id}/analyze-url", 
                            json=data, 
                            name="1_analyze_brand",
                            catch_response=True) as response:
            if response.status_code in [200, 202]:
                response_data = response.json()
                if "job_id" in response_data:
                    self.job_ids.append(response_data["job_id"])
                response.success()
            else:
                response.failure(f"Brand analysis failed: {response.status_code}")
    
    @task
    def step_2_create_campaign(self):
        """Step 2: Create marketing campaign."""
        data = {
            "brand_id": self.brand_id,
            "name": f"Campaign {random.randint(1, 1000)}",
            "description": "AI-generated marketing campaign",
            "target_audience": "young adults",
            "platforms": ["tiktok", "instagram"]
        }
        
        with self.client.post("/api/v1/campaigns", 
                            json=data,
                            name="2_create_campaign",
                            catch_response=True) as response:
            if response.status_code in [200, 201]:
                response_data = response.json()
                self.campaign_id = response_data.get("id")
                response.success()
            else:
                response.failure(f"Campaign creation failed: {response.status_code}")
    
    @task
    def step_3_generate_ideas(self):
        """Step 3: Generate content ideas."""
        if not self.campaign_id:
            return
        
        data = {
            "campaign_id": self.campaign_id,
            "count": 5,
            "content_types": ["video", "ugc"]
        }
        
        with self.client.post(f"/api/v1/content/{self.brand_id}/generate-ideas",
                            json=data,
                            name="3_generate_ideas",
                            catch_response=True) as response:
            if response.status_code in [200, 202]:
                response_data = response.json()
                if "job_id" in response_data:
                    self.job_ids.append(response_data["job_id"])
                response.success()
            else:
                response.failure(f"Idea generation failed: {response.status_code}")
    
    @task
    def step_4_generate_video(self):
        """Step 4: Generate video content."""
        data = {
            "blueprint_id": f"blueprint-{random.randint(1, 100)}",
            "platform": random.choice(["tiktok", "instagram"]),
            "duration": random.choice([15, 30, 60]),
            "style": random.choice(["professional", "casual", "energetic"])
        }
        
        with self.client.post("/api/v1/video-generation/projects",
                            json=data,
                            name="4_generate_video",
                            catch_response=True) as response:
            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                self.video_project_id = response_data.get("id")
                if "job_id" in response_data:
                    self.job_ids.append(response_data["job_id"])
                response.success()
            else:
                response.failure(f"Video generation failed: {response.status_code}")
    
    @task
    def step_5_post_to_social_media(self):
        """Step 5: Post content to social media."""
        if not self.video_project_id:
            return
        
        data = {
            "video_id": self.video_project_id,
            "platforms": ["tiktok", "instagram"],
            "captions": {
                "tiktok": f"Amazing content #{random.randint(1, 1000)} #viral #trending",
                "instagram": f"Check out our latest innovation! #brand #newproduct #{random.randint(1, 1000)}"
            },
            "schedule": "immediate"
        }
        
        with self.client.post("/api/v1/social-media/post-multi-platform",
                            json=data,
                            name="5_post_social_media",
                            catch_response=True) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Social media posting failed: {response.status_code}")
    
    @task
    def step_6_check_analytics(self):
        """Step 6: Check analytics and performance."""
        endpoints = [
            (f"/api/v1/analytics/{self.brand_id}/kpis", "6a_analytics_kpis"),
            (f"/api/v1/analytics/{self.brand_id}/chart-data?metric=views", "6b_analytics_charts"),
            (f"/api/v1/analytics/{self.brand_id}/insights", "6c_analytics_insights")
        ]
        
        for endpoint, name in endpoints:
            with self.client.get(endpoint, 
                               name=name,
                               catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Analytics endpoint failed: {endpoint}")


class ViralOSApiUser(HttpUser):
    """Standard API user for general load testing."""
    
    wait_time = between(1, 5)
    weight = 3  # 3x more likely to be chosen than workflow users
    
    def on_start(self):
        """Set up user session."""
        self.brand_id = f"brand-{random.randint(1, 100)}"
        # Simulate authentication
        self.client.headers.update({
            "Authorization": f"Bearer token-{random.randint(1000, 9999)}",
            "Content-Type": "application/json"
        })
    
    @task(5)
    def browse_dashboard(self):
        """Simulate browsing dashboard."""
        endpoints = [
            "/api/v1/brands",
            f"/api/v1/brands/{self.brand_id}",
            f"/api/v1/campaigns?brand_id={self.brand_id}",
            f"/api/v1/content/{self.brand_id}/ideas"
        ]
        
        endpoint = random.choice(endpoints)
        self.client.get(endpoint, name="browse_dashboard")
    
    @task(3)
    def analyze_trends(self):
        """Simulate TikTok trend analysis."""
        params = {
            "hashtag": f"trend{random.randint(1, 100)}",
            "region": random.choice(["US", "UK", "CA"]),
            "period": random.choice(["7d", "30d", "90d"])
        }
        
        self.client.get("/api/v1/tiktok/trends", 
                       params=params,
                       name="analyze_trends")
    
    @task(2)
    def check_job_status(self):
        """Simulate checking job status."""
        job_id = f"job-{random.randint(1, 1000)}"
        self.client.get(f"/api/v1/jobs/{job_id}/status",
                       name="check_job_status")
    
    @task(1)
    def upload_asset(self):
        """Simulate asset upload."""
        files = {"file": ("test.jpg", b"fake image data", "image/jpeg")}
        data = {"type": "logo", "brand_id": self.brand_id}
        
        self.client.post("/api/v1/assets/upload",
                        files=files,
                        data=data,
                        name="upload_asset")


class ViralOSWorkflowUser(HttpUser):
    """User that executes complete workflows."""
    
    tasks = [BrandWorkflowTaskSet]
    wait_time = between(5, 15)  # Longer wait between complete workflows
    weight = 1  # Less frequent than general API users
    
    def on_start(self):
        """Set up workflow user."""
        self.client.headers.update({
            "Authorization": f"Bearer workflow-token-{random.randint(1000, 9999)}",
            "Content-Type": "application/json"
        })


class ViralOSAnalyticsUser(HttpUser):
    """User focused on analytics and reporting."""
    
    wait_time = between(2, 8)
    weight = 2
    
    def on_start(self):
        """Set up analytics user."""
        self.brand_id = f"brand-{random.randint(1, 50)}"
        self.client.headers.update({
            "Authorization": f"Bearer analytics-token-{random.randint(1000, 9999)}",
            "Content-Type": "application/json"
        })
    
    @task(4)
    def view_kpis(self):
        """View KPI dashboard."""
        params = {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "metrics": "views,engagement,conversion"
        }
        
        self.client.get(f"/api/v1/analytics/{self.brand_id}/kpis",
                       params=params,
                       name="view_kpis")
    
    @task(3)
    def view_charts(self):
        """View analytics charts."""
        metrics = ["views", "engagement", "reach", "conversion"]
        metric = random.choice(metrics)
        
        params = {
            "metric": metric,
            "period": random.choice(["7d", "30d", "90d"]),
            "granularity": random.choice(["day", "week", "month"])
        }
        
        self.client.get(f"/api/v1/analytics/{self.brand_id}/chart-data",
                       params=params,
                       name="view_charts")
    
    @task(2)
    def export_data(self):
        """Export analytics data."""
        params = {
            "format": random.choice(["csv", "json", "xlsx"]),
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }
        
        self.client.get(f"/api/v1/analytics/{self.brand_id}/export",
                       params=params,
                       name="export_data")
    
    @task(2)
    def view_content_performance(self):
        """View content performance metrics."""
        params = {
            "platform": random.choice(["tiktok", "instagram", "all"]),
            "sort": random.choice(["views", "engagement", "date"]),
            "limit": random.randint(10, 50)
        }
        
        self.client.get(f"/api/v1/analytics/{self.brand_id}/content-performance",
                       params=params,
                       name="view_content_performance")


# Locust configuration
class ViralOSLoadTest:
    """Main load test configuration."""
    
    # User distribution
    user_classes = [
        ViralOSApiUser,        # 60% - General API usage
        ViralOSAnalyticsUser,  # 30% - Analytics focused
        ViralOSWorkflowUser    # 10% - Complete workflows
    ]
    
    # Performance thresholds
    RESPONSE_TIME_THRESHOLDS = {
        "browse_dashboard": 500,      # 500ms
        "analyze_trends": 1000,       # 1s
        "view_kpis": 800,            # 800ms
        "view_charts": 1200,         # 1.2s
        "1_analyze_brand": 3000,     # 3s
        "4_generate_video": 10000,   # 10s
        "5_post_social_media": 5000, # 5s
    }
    
    ERROR_RATE_THRESHOLD = 0.05  # 5% error rate
    
    @staticmethod
    def get_failure_threshold():
        """Get failure rate threshold for test termination."""
        return 0.1  # Fail if 10% of requests fail


# Custom event listeners for monitoring
from locust import events

@events.request.add_listener
def request_handler(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Handle individual request metrics."""
    if exception:
        print(f"Request failed: {name} - {exception}")
    
    # Check response time thresholds
    threshold = ViralOSLoadTest.RESPONSE_TIME_THRESHOLDS.get(name, 2000)
    if response_time > threshold:
        print(f"Slow response: {name} took {response_time}ms (threshold: {threshold}ms)")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Handle test start event."""
    print(f"Load test starting with {environment.runner.user_count} users")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Handle test completion and generate summary."""
    stats = environment.runner.stats
    
    print("\n" + "="*50)
    print("LOAD TEST SUMMARY")
    print("="*50)
    
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Requests/sec: {stats.total.avg_content_length:.2f}")
    
    # Performance evaluation
    error_rate = stats.total.num_failures / stats.total.num_requests if stats.total.num_requests > 0 else 0
    print(f"Error rate: {error_rate:.2%}")
    
    if error_rate > ViralOSLoadTest.ERROR_RATE_THRESHOLD:
        print("❌ ERROR RATE TOO HIGH!")
    else:
        print("✅ Error rate within acceptable limits")
    
    # Check individual endpoint performance
    print("\nEndpoint Performance:")
    for name, entry in stats.entries.items():
        if entry.num_requests > 0:
            threshold = ViralOSLoadTest.RESPONSE_TIME_THRESHOLDS.get(name[1], 2000)  # name is (method, name)
            avg_time = entry.avg_response_time
            status = "✅" if avg_time <= threshold else "❌"
            print(f"  {status} {name[1]}: {avg_time:.0f}ms (threshold: {threshold}ms)")