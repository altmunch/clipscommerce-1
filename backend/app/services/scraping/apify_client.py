"""
Apify API Client for TikTok Trend Scraping

Manages interactions with Apify platform for running TikTok trend scrapers,
fetching results, and monitoring scraping jobs. Provides a robust interface
for the ViralOS TikTok trend analysis pipeline.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Callable

import aiohttp
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class ApifyJobStatus(str, Enum):
    """Apify job status enumeration"""
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED-OUT"
    ABORTED = "ABORTED"


class ScrapingMode(str, Enum):
    """TikTok scraping modes"""
    TRENDING = "trending"
    HASHTAG = "hashtag"
    SOUND = "sound"
    USER = "user"
    DISCOVER = "discover"


class ApifyClientError(Exception):
    """Base exception for Apify client errors"""
    pass


class ApifyAuthError(ApifyClientError):
    """Authentication error with Apify API"""
    pass


class ApifyRateLimitError(ApifyClientError):
    """Rate limit exceeded error"""
    pass


class ApifyJobError(ApifyClientError):
    """Job execution error"""
    pass


class ApifyTikTokClient:
    """
    Apify API client for TikTok trend scraping operations.
    
    Handles actor runs, result fetching, job monitoring, and error management
    for the ViralOS TikTok trend analysis pipeline.
    """
    
    def __init__(
        self,
        api_token: str = None,
        actor_id: str = None,
        timeout: int = 300,
        max_retries: int = 3
    ):
        self.api_token = api_token or settings.APIFY_API_TOKEN
        self.actor_id = actor_id or settings.APIFY_TIKTOK_ACTOR_ID
        self.base_url = "https://api.apify.com/v2"
        self.timeout = timeout
        self.max_retries = max_retries
        
        if not self.api_token:
            raise ApifyAuthError("Apify API token is required")
        
        # HTTP client configuration
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "ViralOS-TikTok-Client/1.0.0"
        }
        
        # Rate limiting
        self.rate_limit_window = 60  # seconds
        self.rate_limit_requests = 100  # requests per window
        self.request_times = []
        
        # Active runs tracking
        self.active_runs = {}
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if hasattr(self, 'session'):
            await self.session.close()
    
    def _check_rate_limit(self):
        """Check if rate limit is exceeded"""
        now = time.time()
        
        # Remove old requests outside the window
        self.request_times = [
            req_time for req_time in self.request_times
            if now - req_time < self.rate_limit_window
        ]
        
        # Check if we've exceeded the limit
        if len(self.request_times) >= self.rate_limit_requests:
            raise ApifyRateLimitError(
                f"Rate limit exceeded: {len(self.request_times)} requests in last {self.rate_limit_window}s"
            )
        
        # Record this request
        self.request_times.append(now)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, ApifyRateLimitError))
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Apify API with retry logic"""
        
        self._check_rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        logger.debug(f"Making {method} request to {url}")
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params
            ) as response:
                
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Retry after {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise ApifyRateLimitError("Rate limit exceeded")
                
                if response.status == 401:
                    raise ApifyAuthError("Invalid API token")
                
                if response.status == 404:
                    raise ApifyClientError(f"Resource not found: {url}")
                
                response_data = await response.json()
                
                if not response.ok:
                    error_msg = response_data.get('error', {}).get('message', 'Unknown error')
                    raise ApifyClientError(f"API error ({response.status}): {error_msg}")
                
                return response_data
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            raise ApifyClientError(f"HTTP client error: {e}")
    
    async def start_trending_scrape(
        self,
        max_videos: int = 1000,
        regions: List[str] = None,
        languages: List[str] = None,
        min_engagement: int = 100,
        include_analysis: bool = True,
        proxy_groups: List[str] = None
    ) -> str:
        """
        Start trending content scraping job
        
        Args:
            max_videos: Maximum number of videos to scrape
            regions: Geographic regions to focus on
            languages: Languages to focus on
            min_engagement: Minimum engagement threshold
            include_analysis: Whether to include content analysis
            proxy_groups: Proxy groups to use
            
        Returns:
            str: Run ID of the started job
        """
        
        input_data = {
            "mode": ScrapingMode.TRENDING.value,
            "maxVideos": max_videos,
            "regions": regions or ["US", "UK", "CA", "AU"],
            "languages": languages or ["en"],
            "minEngagement": min_engagement,
            "includeVideoAnalysis": include_analysis,
            "includeEngagementMetrics": True,
            "includeTrendAnalysis": include_analysis,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": proxy_groups or ["RESIDENTIAL"]
            },
            "outputFormat": "json"
        }
        
        return await self._start_actor_run(input_data, "trending_scrape")
    
    async def start_hashtag_scrape(
        self,
        hashtags: List[str],
        max_videos: int = 2000,
        regions: List[str] = None,
        include_analysis: bool = True
    ) -> str:
        """
        Start hashtag-specific scraping job
        
        Args:
            hashtags: List of hashtags to scrape (with or without #)
            max_videos: Maximum number of videos to scrape
            regions: Geographic regions to focus on
            include_analysis: Whether to include content analysis
            
        Returns:
            str: Run ID of the started job
        """
        
        # Ensure hashtags have # prefix
        formatted_hashtags = [
            tag if tag.startswith('#') else f'#{tag}' 
            for tag in hashtags
        ]
        
        input_data = {
            "mode": ScrapingMode.HASHTAG.value,
            "targets": formatted_hashtags,
            "maxVideos": max_videos,
            "regions": regions or ["US", "UK", "CA", "AU"],
            "languages": ["en"],
            "includeVideoAnalysis": include_analysis,
            "includeEngagementMetrics": True,
            "includeTrendAnalysis": include_analysis,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        return await self._start_actor_run(input_data, "hashtag_scrape")
    
    async def start_sound_scrape(
        self,
        sound_ids: List[str],
        max_videos: int = 1500,
        include_analysis: bool = True
    ) -> str:
        """
        Start sound-specific scraping job
        
        Args:
            sound_ids: List of TikTok sound IDs to scrape
            max_videos: Maximum number of videos to scrape
            include_analysis: Whether to include content analysis
            
        Returns:
            str: Run ID of the started job
        """
        
        input_data = {
            "mode": ScrapingMode.SOUND.value,
            "targets": sound_ids,
            "maxVideos": max_videos,
            "includeVideoAnalysis": include_analysis,
            "includeEngagementMetrics": True,
            "includeTrendAnalysis": include_analysis,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        return await self._start_actor_run(input_data, "sound_scrape")
    
    async def start_user_scrape(
        self,
        usernames: List[str],
        max_videos: int = 500,
        include_analysis: bool = True
    ) -> str:
        """
        Start user-specific scraping job
        
        Args:
            usernames: List of TikTok usernames to scrape (with or without @)
            max_videos: Maximum number of videos to scrape
            include_analysis: Whether to include content analysis
            
        Returns:
            str: Run ID of the started job
        """
        
        # Ensure usernames have @ prefix
        formatted_usernames = [
            username if username.startswith('@') else f'@{username}'
            for username in usernames
        ]
        
        input_data = {
            "mode": ScrapingMode.USER.value,
            "targets": formatted_usernames,
            "maxVideos": max_videos,
            "includeVideoAnalysis": include_analysis,
            "includeEngagementMetrics": True,
            "includeTrendAnalysis": include_analysis,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        return await self._start_actor_run(input_data, "user_scrape")
    
    async def start_discover_scrape(
        self,
        regions: List[str] = None,
        include_analysis: bool = True
    ) -> str:
        """
        Start discover page scraping job
        
        Args:
            regions: Geographic regions to focus on
            include_analysis: Whether to include content analysis
            
        Returns:
            str: Run ID of the started job
        """
        
        input_data = {
            "mode": ScrapingMode.DISCOVER.value,
            "regions": regions or ["US", "UK", "CA", "AU"],
            "includeVideoAnalysis": include_analysis,
            "includeEngagementMetrics": True,
            "includeTrendAnalysis": include_analysis,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        return await self._start_actor_run(input_data, "discover_scrape")
    
    async def _start_actor_run(self, input_data: Dict[str, Any], job_type: str) -> str:
        """Start actor run with given input data"""
        
        run_id = str(uuid.uuid4())
        
        logger.info(f"Starting {job_type} scraping job: {run_id}")
        
        endpoint = f"/acts/{self.actor_id}/runs"
        
        payload = {
            "runId": run_id,
            "input": input_data,
            "timeout": self.timeout,
            "memory": 4096,  # 4GB memory
            "build": "latest"
        }
        
        try:
            response = await self._make_request("POST", endpoint, data=payload)
            
            apify_run_id = response["data"]["id"]
            
            # Track the run
            self.active_runs[run_id] = {
                "apify_run_id": apify_run_id,
                "job_type": job_type,
                "started_at": datetime.utcnow(),
                "input_data": input_data,
                "status": ApifyJobStatus.RUNNING
            }
            
            logger.info(f"Started scraping job {run_id} -> Apify run {apify_run_id}")
            
            return run_id
            
        except Exception as e:
            logger.error(f"Failed to start scraping job {run_id}: {e}")
            raise ApifyJobError(f"Failed to start scraping job: {e}")
    
    async def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Get status of a running job
        
        Args:
            run_id: Our internal run ID
            
        Returns:
            Dict containing run status and metadata
        """
        
        if run_id not in self.active_runs:
            raise ApifyJobError(f"Unknown run ID: {run_id}")
        
        run_info = self.active_runs[run_id]
        apify_run_id = run_info["apify_run_id"]
        
        endpoint = f"/actor-runs/{apify_run_id}"
        
        try:
            response = await self._make_request("GET", endpoint)
            run_data = response["data"]
            
            status = ApifyJobStatus(run_data["status"])
            
            # Update our tracking
            run_info["status"] = status
            run_info["last_checked"] = datetime.utcnow()
            
            if status in [ApifyJobStatus.SUCCEEDED, ApifyJobStatus.FAILED, ApifyJobStatus.ABORTED]:
                run_info["finished_at"] = datetime.utcnow()
            
            return {
                "run_id": run_id,
                "apify_run_id": apify_run_id,
                "status": status.value,
                "job_type": run_info["job_type"],
                "started_at": run_info["started_at"].isoformat(),
                "finished_at": run_info.get("finished_at", {}).isoformat() if run_info.get("finished_at") else None,
                "stats": run_data.get("stats", {}),
                "usage": run_data.get("usage", {}),
                "meta": run_data.get("meta", {})
            }
            
        except Exception as e:
            logger.error(f"Failed to get run status for {run_id}: {e}")
            raise ApifyJobError(f"Failed to get run status: {e}")
    
    async def wait_for_completion(
        self,
        run_id: str,
        timeout: int = 1800,  # 30 minutes
        poll_interval: int = 30  # 30 seconds
    ) -> Dict[str, Any]:
        """
        Wait for a job to complete
        
        Args:
            run_id: Our internal run ID
            timeout: Maximum time to wait in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Dict containing final run status
        """
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status_info = await self.get_run_status(run_id)
            status = ApifyJobStatus(status_info["status"])
            
            if status in [ApifyJobStatus.SUCCEEDED, ApifyJobStatus.FAILED, ApifyJobStatus.ABORTED, ApifyJobStatus.TIMED_OUT]:
                return status_info
            
            logger.info(f"Job {run_id} still running... (status: {status.value})")
            await asyncio.sleep(poll_interval)
        
        raise ApifyJobError(f"Job {run_id} timed out after {timeout} seconds")
    
    async def get_run_results(self, run_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get results from a completed job
        
        Args:
            run_id: Our internal run ID
            limit: Maximum number of results to return
            
        Returns:
            List of scraped video data
        """
        
        if run_id not in self.active_runs:
            raise ApifyJobError(f"Unknown run ID: {run_id}")
        
        run_info = self.active_runs[run_id]
        apify_run_id = run_info["apify_run_id"]
        
        # Check if job is completed
        status_info = await self.get_run_status(run_id)
        if status_info["status"] != ApifyJobStatus.SUCCEEDED.value:
            raise ApifyJobError(f"Job {run_id} has not completed successfully. Status: {status_info['status']}")
        
        endpoint = f"/actor-runs/{apify_run_id}/dataset/items"
        params = {"format": "json"}
        
        if limit:
            params["limit"] = limit
        
        try:
            response = await self._make_request("GET", endpoint, params=params)
            results = response
            
            logger.info(f"Retrieved {len(results)} results for job {run_id}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get results for job {run_id}: {e}")
            raise ApifyJobError(f"Failed to get results: {e}")
    
    async def get_run_analytics(self, run_id: str) -> Dict[str, Any]:
        """
        Get analytics data from a completed job
        
        Args:
            run_id: Our internal run ID
            
        Returns:
            Dict containing analytics data
        """
        
        if run_id not in self.active_runs:
            raise ApifyJobError(f"Unknown run ID: {run_id}")
        
        run_info = self.active_runs[run_id]
        apify_run_id = run_info["apify_run_id"]
        
        endpoint = f"/actor-runs/{apify_run_id}/key-value-store/records/ANALYTICS"
        
        try:
            response = await self._make_request("GET", endpoint)
            return response
            
        except Exception as e:
            logger.warning(f"No analytics data found for job {run_id}: {e}")
            return {}
    
    async def get_trend_analysis(self, run_id: str) -> Dict[str, Any]:
        """
        Get trend analysis data from a completed job
        
        Args:
            run_id: Our internal run ID
            
        Returns:
            Dict containing trend analysis data
        """
        
        if run_id not in self.active_runs:
            raise ApifyJobError(f"Unknown run ID: {run_id}")
        
        run_info = self.active_runs[run_id]
        apify_run_id = run_info["apify_run_id"]
        
        endpoint = f"/actor-runs/{apify_run_id}/key-value-store/records/TREND_ANALYSIS"
        
        try:
            response = await self._make_request("GET", endpoint)
            return response
            
        except Exception as e:
            logger.warning(f"No trend analysis data found for job {run_id}: {e}")
            return {}
    
    async def abort_run(self, run_id: str) -> bool:
        """
        Abort a running job
        
        Args:
            run_id: Our internal run ID
            
        Returns:
            bool: True if successfully aborted
        """
        
        if run_id not in self.active_runs:
            raise ApifyJobError(f"Unknown run ID: {run_id}")
        
        run_info = self.active_runs[run_id]
        apify_run_id = run_info["apify_run_id"]
        
        endpoint = f"/actor-runs/{apify_run_id}/abort"
        
        try:
            await self._make_request("POST", endpoint)
            
            # Update our tracking
            run_info["status"] = ApifyJobStatus.ABORTED
            run_info["finished_at"] = datetime.utcnow()
            
            logger.info(f"Successfully aborted job {run_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to abort job {run_id}: {e}")
            raise ApifyJobError(f"Failed to abort job: {e}")
    
    async def list_active_runs(self) -> List[Dict[str, Any]]:
        """
        List all active runs
        
        Returns:
            List of active run information
        """
        
        active_runs = []
        
        for run_id, run_info in self.active_runs.items():
            if run_info["status"] == ApifyJobStatus.RUNNING:
                try:
                    status_info = await self.get_run_status(run_id)
                    active_runs.append(status_info)
                except Exception as e:
                    logger.warning(f"Failed to get status for run {run_id}: {e}")
        
        return active_runs
    
    async def cleanup_old_runs(self, max_age_hours: int = 24):
        """
        Clean up tracking data for old runs
        
        Args:
            max_age_hours: Maximum age in hours for keeping run data
        """
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for run_id, run_info in self.active_runs.items():
            if run_info["started_at"] < cutoff_time:
                to_remove.append(run_id)
        
        for run_id in to_remove:
            del self.active_runs[run_id]
            logger.debug(f"Cleaned up old run data for {run_id}")
        
        logger.info(f"Cleaned up {len(to_remove)} old run records")
    
    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """
        Get summary information for a run
        
        Args:
            run_id: Our internal run ID
            
        Returns:
            Dict containing run summary
        """
        
        if run_id not in self.active_runs:
            raise ApifyJobError(f"Unknown run ID: {run_id}")
        
        run_info = self.active_runs[run_id]
        
        duration = None
        if run_info.get("finished_at"):
            duration = (run_info["finished_at"] - run_info["started_at"]).total_seconds()
        
        return {
            "run_id": run_id,
            "apify_run_id": run_info["apify_run_id"],
            "job_type": run_info["job_type"],
            "status": run_info["status"].value,
            "started_at": run_info["started_at"].isoformat(),
            "finished_at": run_info.get("finished_at", {}).isoformat() if run_info.get("finished_at") else None,
            "duration_seconds": duration,
            "input_summary": self._summarize_input(run_info["input_data"])
        }
    
    def _summarize_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize input data for display"""
        
        summary = {
            "mode": input_data.get("mode"),
            "max_videos": input_data.get("maxVideos"),
            "regions": input_data.get("regions", []),
        }
        
        if "targets" in input_data:
            summary["targets"] = input_data["targets"][:5]  # First 5 targets
            if len(input_data["targets"]) > 5:
                summary["targets_total"] = len(input_data["targets"])
        
        return summary


# Global client instance
_apify_client: Optional[ApifyTikTokClient] = None


async def get_apify_client() -> ApifyTikTokClient:
    """Get global Apify client instance"""
    global _apify_client
    
    if _apify_client is None:
        _apify_client = ApifyTikTokClient()
    
    return _apify_client


async def close_apify_client():
    """Close global Apify client"""
    global _apify_client
    
    if _apify_client:
        if hasattr(_apify_client, 'session'):
            await _apify_client.session.close()
        _apify_client = None


# Convenience functions for common operations
async def start_trending_analysis(
    max_videos: int = 1000,
    regions: List[str] = None,
    include_analysis: bool = True
) -> str:
    """Start trending content analysis"""
    async with ApifyTikTokClient() as client:
        return await client.start_trending_scrape(
            max_videos=max_videos,
            regions=regions,
            include_analysis=include_analysis
        )


async def start_hashtag_analysis(
    hashtags: List[str],
    max_videos: int = 2000,
    regions: List[str] = None
) -> str:
    """Start hashtag analysis"""
    async with ApifyTikTokClient() as client:
        return await client.start_hashtag_scrape(
            hashtags=hashtags,
            max_videos=max_videos,
            regions=regions
        )


async def get_scraping_results(run_id: str) -> List[Dict[str, Any]]:
    """Get scraping results for a completed job"""
    async with ApifyTikTokClient() as client:
        return await client.get_run_results(run_id)