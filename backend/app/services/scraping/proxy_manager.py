"""
Proxy rotation and anti-bot detection system for scraping.
"""

import asyncio
import random
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse
import logging

import aiohttp
import requests
from fake_useragent import UserAgent
from user_agents import parse as parse_user_agent

logger = logging.getLogger(__name__)


@dataclass
class ProxyInfo:
    """Proxy configuration information"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    country: Optional[str] = None
    speed: float = 0.0  # Response time in seconds
    success_rate: float = 1.0  # Success rate (0-1)
    last_used: float = 0.0
    failure_count: int = 0
    is_working: bool = True
    
    @property
    def url(self) -> str:
        """Get proxy URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def dict(self) -> Dict[str, str]:
        """Get proxy dict for requests library"""
        return {
            "http": self.url,
            "https": self.url
        }


class ProxyManager:
    """Manages proxy rotation and health checking"""
    
    def __init__(self, 
                 proxies: List[Dict[str, Any]] = None,
                 max_failures: int = 3,
                 cooldown_time: int = 300,  # 5 minutes
                 health_check_interval: int = 3600):  # 1 hour
        
        self.proxies: List[ProxyInfo] = []
        self.max_failures = max_failures
        self.cooldown_time = cooldown_time
        self.health_check_interval = health_check_interval
        self.last_health_check = 0
        
        # Load proxies if provided
        if proxies:
            self.load_proxies(proxies)
        
        # Free proxy sources (for testing - not recommended for production)
        self.free_proxy_apis = [
            "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
        ]
    
    def load_proxies(self, proxy_configs: List[Dict[str, Any]]):
        """Load proxy configurations"""
        for config in proxy_configs:
            proxy = ProxyInfo(
                host=config["host"],
                port=config["port"],
                username=config.get("username"),
                password=config.get("password"),
                protocol=config.get("protocol", "http"),
                country=config.get("country")
            )
            self.proxies.append(proxy)
        
        logger.info(f"Loaded {len(self.proxies)} proxies")
    
    async def get_working_proxy(self) -> Optional[ProxyInfo]:
        """Get a working proxy with lowest failure rate"""
        
        # Health check if needed
        if time.time() - self.last_health_check > self.health_check_interval:
            await self.health_check_all()
        
        # Filter working proxies not in cooldown
        current_time = time.time()
        available_proxies = [
            p for p in self.proxies 
            if p.is_working and 
            p.failure_count < self.max_failures and
            (current_time - p.last_used) > random.uniform(10, 30)  # Random delay
        ]
        
        if not available_proxies:
            logger.warning("No working proxies available")
            return None
        
        # Sort by success rate and last used time
        available_proxies.sort(
            key=lambda p: (p.success_rate, -p.last_used), 
            reverse=True
        )
        
        # Select with weighted randomness (favor better proxies)
        weights = [p.success_rate ** 2 for p in available_proxies[:10]]  # Top 10
        selected = random.choices(available_proxies[:10], weights=weights)[0]
        
        selected.last_used = current_time
        return selected
    
    async def mark_proxy_success(self, proxy: ProxyInfo, response_time: float):
        """Mark proxy as successful"""
        proxy.speed = response_time
        proxy.failure_count = 0
        proxy.success_rate = min(proxy.success_rate + 0.1, 1.0)
        proxy.is_working = True
    
    async def mark_proxy_failure(self, proxy: ProxyInfo, error: str):
        """Mark proxy as failed"""
        proxy.failure_count += 1
        proxy.success_rate = max(proxy.success_rate - 0.2, 0.0)
        
        if proxy.failure_count >= self.max_failures:
            proxy.is_working = False
            logger.warning(f"Proxy {proxy.host}:{proxy.port} marked as not working: {error}")
    
    async def health_check_proxy(self, proxy: ProxyInfo) -> bool:
        """Check if a proxy is working"""
        test_urls = [
            "http://httpbin.org/ip",
            "https://api.ipify.org?format=json",
            "http://icanhazip.com"
        ]
        
        for test_url in test_urls:
            try:
                async with aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(limit=1),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as session:
                    
                    start_time = time.time()
                    async with session.get(
                        test_url, 
                        proxy=proxy.url,
                        headers={"User-Agent": UserAgent().random}
                    ) as response:
                        
                        if response.status == 200:
                            response_time = time.time() - start_time
                            await self.mark_proxy_success(proxy, response_time)
                            return True
                        
            except Exception as e:
                logger.debug(f"Proxy health check failed for {proxy.host}:{proxy.port}: {e}")
                continue
        
        await self.mark_proxy_failure(proxy, "Health check failed")
        return False
    
    async def health_check_all(self):
        """Health check all proxies"""
        logger.info("Starting proxy health check...")
        
        tasks = [self.health_check_proxy(proxy) for proxy in self.proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        working_count = sum(1 for r in results if r is True)
        self.last_health_check = time.time()
        
        logger.info(f"Health check complete: {working_count}/{len(self.proxies)} proxies working")
    
    async def fetch_free_proxies(self) -> List[str]:
        """Fetch free proxies (for testing only)"""
        proxies = []
        
        for api_url in self.free_proxy_apis:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(api_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            
                            # Parse proxy list
                            lines = content.strip().split('\n')
                            for line in lines:
                                line = line.strip()
                                if ':' in line and len(line.split(':')) == 2:
                                    host, port = line.split(':')
                                    try:
                                        port = int(port)
                                        if 1 <= port <= 65535:
                                            proxies.append(f"{host}:{port}")
                                    except ValueError:
                                        continue
                            
                            # Limit to avoid too many bad proxies
                            if len(proxies) > 50:
                                break
                                
            except Exception as e:
                logger.debug(f"Failed to fetch from {api_url}: {e}")
                continue
        
        return proxies[:100]  # Limit to 100 free proxies
    
    async def load_free_proxies(self):
        """Load free proxies for testing"""
        proxy_list = await self.fetch_free_proxies()
        
        for proxy_str in proxy_list:
            if ':' in proxy_str:
                host, port = proxy_str.split(':')
                try:
                    proxy = ProxyInfo(host=host, port=int(port))
                    self.proxies.append(proxy)
                except ValueError:
                    continue
        
        logger.info(f"Loaded {len(proxy_list)} free proxies")


class AntiDetectionManager:
    """Manages anti-detection measures"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session_cookies = {}
        self.request_history = {}
        
        # Browser fingerprint components
        self.screen_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (1600, 900), (2560, 1440), (1920, 1200)
        ]
        
        self.languages = [
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9",
            "en-CA,en;q=0.9",
            "en-AU,en;q=0.9"
        ]
        
        self.timezones = [
            "America/New_York", "America/Los_Angeles", "America/Chicago",
            "Europe/London", "Europe/Berlin", "Asia/Tokyo"
        ]
    
    def get_random_headers(self, url: str = None) -> Dict[str, str]:
        """Generate random but realistic headers"""
        
        user_agent = self.ua.random
        ua_parsed = parse_user_agent(user_agent)
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": random.choice(self.languages),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
        
        # Add browser-specific headers
        if ua_parsed.browser.family == "Chrome":
            headers.update({
                "sec-ch-ua": f'"{ua_parsed.browser.family}";v="{ua_parsed.browser.version_string}", "Chromium";v="{ua_parsed.browser.version_string}", ";Not A Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": f'"{ua_parsed.os.family}"'
            })
        
        # Add referer if we have request history for this domain
        if url:
            domain = urlparse(url).netloc
            if domain in self.request_history:
                previous_urls = self.request_history[domain]
                if previous_urls:
                    headers["Referer"] = random.choice(previous_urls[-5:])  # Last 5 URLs
        
        return headers
    
    def get_browser_fingerprint(self) -> Dict[str, Any]:
        """Generate a consistent browser fingerprint"""
        
        screen_width, screen_height = random.choice(self.screen_resolutions)
        
        return {
            "screen": {
                "width": screen_width,
                "height": screen_height,
                "colorDepth": 24,
                "pixelDepth": 24
            },
            "navigator": {
                "language": random.choice(self.languages).split(',')[0],
                "languages": random.choice(self.languages).split(','),
                "platform": random.choice(["Win32", "MacIntel", "Linux x86_64"]),
                "cookieEnabled": True,
                "doNotTrack": "1"
            },
            "timezone": random.choice(self.timezones)
        }
    
    def calculate_delay(self, domain: str, base_delay: Tuple[float, float] = (1.0, 3.0)) -> float:
        """Calculate intelligent delay between requests"""
        
        current_time = time.time()
        
        # Check request history for this domain
        if domain not in self.request_history:
            self.request_history[domain] = []
        
        recent_requests = [
            t for t in self.request_history[domain] 
            if current_time - t < 300  # Last 5 minutes
        ]
        
        # Increase delay based on recent request frequency
        if len(recent_requests) > 10:
            multiplier = 2.0
        elif len(recent_requests) > 5:
            multiplier = 1.5
        else:
            multiplier = 1.0
        
        # Add randomness
        delay = random.uniform(*base_delay) * multiplier
        
        # Add extra delay occasionally to mimic human behavior
        if random.random() < 0.1:  # 10% chance
            delay += random.uniform(5.0, 15.0)
        
        return delay
    
    def record_request(self, url: str):
        """Record request for delay calculation"""
        domain = urlparse(url).netloc
        current_time = time.time()
        
        if domain not in self.request_history:
            self.request_history[domain] = []
        
        self.request_history[domain].append(current_time)
        
        # Keep only recent requests
        cutoff = current_time - 3600  # 1 hour
        self.request_history[domain] = [
            t for t in self.request_history[domain] if t > cutoff
        ]
    
    def detect_bot_protection(self, html_content: str, response_headers: Dict[str, str]) -> Dict[str, Any]:
        """Detect bot protection mechanisms"""
        
        protection_signals = {
            "cloudflare": False,
            "recaptcha": False,
            "imperva": False,
            "datadome": False,
            "akamai": False,
            "rate_limited": False,
            "blocked": False
        }
        
        html_lower = html_content.lower()
        
        # Cloudflare detection
        if any(indicator in html_lower for indicator in [
            "cloudflare", "cf-ray", "checking your browser",
            "please wait while we verify", "ddos protection"
        ]):
            protection_signals["cloudflare"] = True
        
        # reCAPTCHA detection
        if any(indicator in html_lower for indicator in [
            "recaptcha", "g-recaptcha", "grecaptcha",
            "i'm not a robot", "verify you are human"
        ]):
            protection_signals["recaptcha"] = True
        
        # Imperva/Incapsula detection
        if any(indicator in html_lower for indicator in [
            "imperva", "incapsula", "_incap_", "visid_incap"
        ]):
            protection_signals["imperva"] = True
        
        # DataDome detection
        if any(indicator in html_lower for indicator in [
            "datadome", "dd_cookie", "blocked by security policy"
        ]):
            protection_signals["datadome"] = True
        
        # Akamai detection
        if any(indicator in html_lower for indicator in [
            "akamai", "aka_", "reference #18"
        ]):
            protection_signals["akamai"] = True
        
        # Rate limiting detection
        if any(indicator in html_lower for indicator in [
            "rate limit", "too many requests", "429",
            "please slow down", "throttled"
        ]):
            protection_signals["rate_limited"] = True
        
        # General blocking detection
        if any(indicator in html_lower for indicator in [
            "access denied", "blocked", "forbidden",
            "your request has been blocked", "suspicious activity"
        ]):
            protection_signals["blocked"] = True
        
        # Check response headers
        headers_lower = {k.lower(): v.lower() for k, v in response_headers.items()}
        
        if "cf-ray" in headers_lower or "cloudflare" in headers_lower.get("server", ""):
            protection_signals["cloudflare"] = True
        
        if headers_lower.get("x-akamai-transformed"):
            protection_signals["akamai"] = True
        
        return protection_signals
    
    def get_evasion_strategy(self, protection_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Get evasion strategy based on detected protection"""
        
        strategy = {
            "use_proxy": False,
            "increase_delay": False,
            "change_user_agent": False,
            "use_javascript": False,
            "solve_captcha": False,
            "retry_with_session": False,
            "recommended_delay": (2.0, 5.0)
        }
        
        if protection_signals["cloudflare"]:
            strategy.update({
                "use_javascript": True,
                "increase_delay": True,
                "recommended_delay": (5.0, 10.0)
            })
        
        if protection_signals["recaptcha"]:
            strategy.update({
                "solve_captcha": True,
                "use_javascript": True
            })
        
        if protection_signals["rate_limited"]:
            strategy.update({
                "increase_delay": True,
                "use_proxy": True,
                "recommended_delay": (10.0, 30.0)
            })
        
        if protection_signals["blocked"]:
            strategy.update({
                "use_proxy": True,
                "change_user_agent": True,
                "retry_with_session": True
            })
        
        return strategy
    
    async def handle_captcha(self, page_content: str) -> Optional[str]:
        """Handle CAPTCHA solving (placeholder for CAPTCHA service integration)"""
        
        # This would integrate with services like:
        # - 2captcha
        # - Anti-Captcha
        # - DeathByCaptcha
        # - CapMonster
        
        logger.warning("CAPTCHA detected - manual intervention required")
        return None
    
    def rotate_session(self, domain: str):
        """Rotate session for a domain"""
        if domain in self.session_cookies:
            del self.session_cookies[domain]
        
        # Clear request history
        if domain in self.request_history:
            self.request_history[domain] = []