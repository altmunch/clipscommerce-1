"""
Unified HTTP client service for all network requests
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Union, List
from urllib.parse import urljoin, urlparse
import aiohttp
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.security_utils import InputValidator

logger = logging.getLogger(__name__)


class HTTPClientConfig:
    """Configuration for HTTP client"""
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        user_agent: str = None,
        headers: Dict[str, str] = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        max_redirects: int = 10
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.user_agent = user_agent or settings.USER_AGENT
        self.headers = headers or {}
        self.verify_ssl = verify_ssl
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects


class UnifiedHTTPClient:
    """Unified HTTP client with security, retry logic, and standardized error handling"""
    
    def __init__(self, config: HTTPClientConfig = None):
        self.config = config or HTTPClientConfig()
        self._session = None
        self._httpx_client = None
    
    async def __aenter__(self):
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()
    
    async def _create_session(self):
        """Create HTTP session with proper configuration"""
        
        # Default headers
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            **self.config.headers
        }
        
        # aiohttp session for complex scraping
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
            verify_ssl=self.config.verify_ssl
        )
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
            auto_decompress=True
        )
        
        # httpx client for API requests
        self._httpx_client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers=headers,
            verify=self.config.verify_ssl,
            follow_redirects=self.config.follow_redirects,
            max_redirects=self.config.max_redirects
        )
    
    async def _close_session(self):
        """Close HTTP sessions"""
        if self._session:
            await self._session.close()
        
        if self._httpx_client:
            await self._httpx_client.aclose()
    
    def _validate_url(self, url: str) -> str:
        """Validate and sanitize URL"""
        if not InputValidator.validate_url(url):
            raise ValueError(f"Invalid URL: {url}")
        
        # Parse URL to check components
        parsed = urlparse(url)
        
        # Block private IP ranges and localhost in production
        if parsed.hostname:
            if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
                if settings.ENVIRONMENT != "development":
                    raise ValueError("Localhost URLs not allowed in production")
            
            # Block private IP ranges
            if (parsed.hostname.startswith('192.168.') or 
                parsed.hostname.startswith('10.') or 
                parsed.hostname.startswith('172.')):
                if settings.ENVIRONMENT != "development":
                    raise ValueError("Private IP addresses not allowed")
        
        return url
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get(
        self, 
        url: str, 
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        use_aiohttp: bool = False
    ) -> Dict[str, Any]:
        """Make GET request with retry logic"""
        
        validated_url = self._validate_url(url)
        
        try:
            if use_aiohttp:
                return await self._aiohttp_get(validated_url, params, headers)
            else:
                return await self._httpx_get(validated_url, params, headers)
                
        except Exception as e:
            logger.error(f"HTTP GET failed for {url}: {e}")
            raise
    
    async def _httpx_get(
        self, 
        url: str, 
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Make GET request using httpx"""
        
        request_headers = {**self.config.headers}
        if headers:
            request_headers.update(headers)
        
        response = await self._httpx_client.get(
            url,
            params=params,
            headers=request_headers
        )
        
        return await self._process_response(response, "httpx")
    
    async def _aiohttp_get(
        self, 
        url: str, 
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Make GET request using aiohttp"""
        
        request_headers = {**self.config.headers}
        if headers:
            request_headers.update(headers)
        
        async with self._session.get(
            url,
            params=params,
            headers=request_headers
        ) as response:
            return await self._process_response(response, "aiohttp")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def post(
        self,
        url: str,
        data: Union[Dict[str, Any], str] = None,
        json: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        use_aiohttp: bool = False
    ) -> Dict[str, Any]:
        """Make POST request with retry logic"""
        
        validated_url = self._validate_url(url)
        
        try:
            if use_aiohttp:
                return await self._aiohttp_post(validated_url, data, json, headers)
            else:
                return await self._httpx_post(validated_url, data, json, headers)
                
        except Exception as e:
            logger.error(f"HTTP POST failed for {url}: {e}")
            raise
    
    async def _httpx_post(
        self,
        url: str,
        data: Union[Dict[str, Any], str] = None,
        json: Dict[str, Any] = None,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Make POST request using httpx"""
        
        request_headers = {**self.config.headers}
        if headers:
            request_headers.update(headers)
        
        response = await self._httpx_client.post(
            url,
            data=data,
            json=json,
            headers=request_headers
        )
        
        return await self._process_response(response, "httpx")
    
    async def _aiohttp_post(
        self,
        url: str,
        data: Union[Dict[str, Any], str] = None,
        json: Dict[str, Any] = None,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Make POST request using aiohttp"""
        
        request_headers = {**self.config.headers}
        if headers:
            request_headers.update(headers)
        
        async with self._session.post(
            url,
            data=data,
            json=json,
            headers=request_headers
        ) as response:
            return await self._process_response(response, "aiohttp")
    
    async def _process_response(
        self, 
        response: Union[httpx.Response, aiohttp.ClientResponse],
        client_type: str
    ) -> Dict[str, Any]:
        """Process HTTP response and extract data"""
        
        if client_type == "httpx":
            status_code = response.status_code
            headers = dict(response.headers)
            
            # Check if response is successful
            response.raise_for_status()
            
            # Try to parse as JSON first
            content_type = headers.get("content-type", "").lower()
            
            if "application/json" in content_type:
                content = response.json()
            else:
                content = response.text
                
        elif client_type == "aiohttp":
            status_code = response.status
            headers = dict(response.headers)
            
            # Check if response is successful
            if status_code >= 400:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=status_code
                )
            
            # Try to parse as JSON first
            content_type = headers.get("content-type", "").lower()
            
            if "application/json" in content_type:
                content = await response.json()
            else:
                content = await response.text()
        
        return {
            "status_code": status_code,
            "headers": headers,
            "content": content,
            "url": str(response.url),
            "success": 200 <= status_code < 300
        }
    
    async def download_file(
        self,
        url: str,
        destination: str,
        chunk_size: int = 8192,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Download file from URL to destination"""
        
        validated_url = self._validate_url(url)
        
        request_headers = {**self.config.headers}
        if headers:
            request_headers.update(headers)
        
        try:
            async with self._session.get(
                validated_url, 
                headers=request_headers
            ) as response:
                
                if response.status >= 400:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status
                    )
                
                file_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(destination, 'wb') as file:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        file.write(chunk)
                        downloaded += len(chunk)
                
                return {
                    "success": True,
                    "file_size": file_size,
                    "downloaded": downloaded,
                    "destination": destination,
                    "url": validated_url
                }
                
        except Exception as e:
            logger.error(f"File download failed for {url}: {e}")
            raise


# Singleton instance for global use
_http_client = None
_http_config = HTTPClientConfig()


async def get_http_client(config: HTTPClientConfig = None) -> UnifiedHTTPClient:
    """Get configured HTTP client instance"""
    global _http_client, _http_config
    
    if config and config != _http_config:
        if _http_client:
            await _http_client._close_session()
        _http_config = config
        _http_client = None
    
    if not _http_client:
        _http_client = UnifiedHTTPClient(_http_config)
        await _http_client._create_session()
    
    return _http_client


# Convenience functions
async def http_get(url: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for GET requests"""
    client = await get_http_client()
    return await client.get(url, **kwargs)


async def http_post(url: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for POST requests"""
    client = await get_http_client()
    return await client.post(url, **kwargs)


async def download_file(url: str, destination: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for file downloads"""
    client = await get_http_client()
    return await client.download_file(url, destination, **kwargs)