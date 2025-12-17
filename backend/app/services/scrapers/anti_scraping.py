"""
Anti-Scraping Utilities - FAANG-Level Implementation
Handles user-agent rotation, rate limiting, proxy management, and retry logic
"""
from typing import Optional, Dict, Any, List
import random
import asyncio
from datetime import datetime, timedelta
import structlog
from fake_useragent import UserAgent

logger = structlog.get_logger()


class AntiScrapingManager:
    """
    Manages anti-scraping measures with FAANG-level sophistication
    - User-agent rotation
    - Intelligent rate limiting
    - Exponential backoff
    - Request fingerprinting
    """
    
    def __init__(self):
        self.ua = UserAgent()
        self.request_history: Dict[str, List[datetime]] = {}
        self.blocked_domains: Dict[str, datetime] = {}
        
        # Rate limits per domain (requests per minute)
        self.rate_limits = {
            'default': 10,
            'scholarships.com': 5,
            'niche.com': 5,
            'fastweb.com': 8,
            'bold.org': 15,
            'mlh.io': 20,
            'devpost.com': 20,
            'kaggle.com': 30,  # Has API
            'github.com': 60,  # Has API
        }
    
    def get_headers(self, domain: Optional[str] = None) -> Dict[str, str]:
        """
        Get randomized headers for request
        Mimics real browser behavior
        """
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        # Add referer for specific domains
        if domain:
            if 'scholarships.com' in domain:
                headers['Referer'] = 'https://www.google.com/'
            elif 'niche.com' in domain:
                headers['Referer'] = 'https://www.google.com/'
        
        return headers
    
    async def wait_if_needed(self, domain: str):
        """
        Intelligent rate limiting based on domain
        Implements token bucket algorithm
        """
        # Extract base domain
        base_domain = self._extract_domain(domain)
        
        # Check if domain is blocked
        if base_domain in self.blocked_domains:
            block_until = self.blocked_domains[base_domain]
            if datetime.now() < block_until:
                wait_seconds = (block_until - datetime.now()).total_seconds()
                logger.warning(
                    f"Domain {base_domain} is blocked",
                    wait_seconds=wait_seconds
                )
                await asyncio.sleep(wait_seconds)
                del self.blocked_domains[base_domain]
        
        # Get rate limit for domain
        rate_limit = self.rate_limits.get(base_domain, self.rate_limits['default'])
        
        # Track request history
        if base_domain not in self.request_history:
            self.request_history[base_domain] = []
        
        # Remove old requests (older than 1 minute)
        cutoff = datetime.now() - timedelta(minutes=1)
        self.request_history[base_domain] = [
            ts for ts in self.request_history[base_domain]
            if ts > cutoff
        ]
        
        # Check if we're at rate limit
        if len(self.request_history[base_domain]) >= rate_limit:
            # Calculate wait time
            oldest_request = min(self.request_history[base_domain])
            wait_until = oldest_request + timedelta(minutes=1)
            wait_seconds = (wait_until - datetime.now()).total_seconds()
            
            if wait_seconds > 0:
                logger.info(
                    f"Rate limit reached for {base_domain}",
                    wait_seconds=wait_seconds
                )
                await asyncio.sleep(wait_seconds)
        
        # Record this request
        self.request_history[base_domain].append(datetime.now())
    
    def mark_blocked(self, domain: str, duration_minutes: int = 30):
        """Mark a domain as blocked (e.g., after 403/429)"""
        base_domain = self._extract_domain(domain)
        block_until = datetime.now() + timedelta(minutes=duration_minutes)
        self.blocked_domains[base_domain] = block_until
        
        logger.warning(
            f"Marked {base_domain} as blocked",
            duration_minutes=duration_minutes
        )
    
    async def retry_with_backoff(
        self,
        func,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        """
        Retry function with exponential backoff
        FAANG-level retry logic
        """
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                # Calculate delay with exponential backoff + jitter
                delay = min(
                    base_delay * (2 ** attempt) + random.uniform(0, 1),
                    max_delay
                )
                
                logger.warning(
                    f"Retry attempt {attempt + 1}/{max_retries}",
                    error=str(e),
                    delay=delay
                )
                
                await asyncio.sleep(delay)
    
    def _extract_domain(self, url: str) -> str:
        """Extract base domain from URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        
        # Remove www.
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain


# Global instance
anti_scraping_manager = AntiScrapingManager()
