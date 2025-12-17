"""
Base Scraper - Abstract foundation for all opportunity scrapers
Implements common HTTP patterns, rate limiting, error handling, and retry logic
"""

import httpx
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
import random

from app.services.kafka_config import kafka_producer_manager, KafkaConfig

logger = structlog.get_logger()


class BaseScraper(ABC):
    """Abstract base class for all opportunity scrapers"""
    
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        self.rate_limit = 1.5  # seconds between requests
        self.max_retries = 3
        self.timeout = 30
        self.client: Optional[httpx.AsyncClient] = None
        self.kafka_producer = kafka_producer_manager
        self.streaming_enabled = False
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper configuration"""
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self.client
    
    async def _close_client(self):
        """Close HTTP client"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
    
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate request headers with random user agent"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        if additional_headers:
            headers.update(additional_headers)
        
        return headers
    
    async def _fetch_with_retry(
        self,
        url: str,
        method: str = 'GET',
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Optional[httpx.Response]:
        """
        Fetch URL with exponential backoff retry logic
        """
        client = await self._get_client()
        request_headers = self._get_headers(headers)
        
        for attempt in range(self.max_retries):
            try:
                if method.upper() == 'GET':
                    response = await client.get(url, params=params, headers=request_headers)
                elif method.upper() == 'POST':
                    response = await client.post(url, json=json_data, headers=request_headers)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit)
                
                # Check for rate limit responses
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(
                        "Rate limited by server",
                        url=url,
                        retry_after=retry_after,
                        attempt=attempt + 1
                    )
                    await asyncio.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response
                
            except httpx.HTTPStatusError as e:
                logger.error(
                    "HTTP error",
                    url=url,
                    status_code=e.response.status_code,
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )
                
                if attempt < self.max_retries - 1:
                    backoff = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(backoff)
                else:
                    return None
                    
            except httpx.RequestError as e:
                logger.error(
                    "Request error",
                    url=url,
                    error=str(e),
                    attempt=attempt + 1
                )
                
                if attempt < self.max_retries - 1:
                    backoff = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(backoff)
                else:
                    return None
            
            except Exception as e:
                logger.error(
                    "Unexpected error",
                    url=url,
                    error=str(e),
                    attempt=attempt + 1
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    return None
        
        return None
    
    def _safe_get(self, data: Dict, *keys, default=None) -> Any:
        """Safely navigate nested dictionary"""
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            else:
                return default
        return current if current is not None else default

    def enable_streaming(self):
        """Enable Kafka streaming for real-time data publishing"""
        self.streaming_enabled = self.kafka_producer.initialize()
        if self.streaming_enabled:
            logger.info(
                "Real-time streaming enabled",
                source=self.get_source_name()
            )
        else:
            logger.info(
                "Streaming disabled - running in batch mode",
                source=self.get_source_name()
            )
        return self.streaming_enabled

    def publish_to_stream(self, raw_data: Dict[str, Any]) -> bool:
        """
        Publish raw scraped data to Confluent Kafka stream

        Args:
            raw_data: Raw opportunity data from scraper

        Returns:
            True if published successfully, False if streaming disabled or failed
        """
        if not self.streaming_enabled:
            return False

        source_name = self.get_source_name()

        message_payload = {
            'source': source_name,
            'raw_data': raw_data,
            'scraped_at': datetime.utcnow().isoformat(),
            'scraper_version': '1.0.0'
        }

        success = self.kafka_producer.publish_to_stream(
            topic=KafkaConfig.RAW_OPPORTUNITIES_TOPIC,
            key=source_name,
            value=message_payload
        )

        if success:
            logger.debug(
                "Opportunity published to stream",
                source=source_name,
                opportunity_name=raw_data.get('name', 'Unknown')
            )

        return success

    async def scrape_and_stream(self) -> List[Dict[str, Any]]:
        """
        Scrape opportunities and optionally stream them in real-time
        Returns scraped opportunities for backward compatibility
        """
        opportunities = await self.scrape()

        if self.streaming_enabled:
            logger.info(
                "Publishing opportunities to stream",
                source=self.get_source_name(),
                count=len(opportunities)
            )

            for opp in opportunities:
                self.publish_to_stream(opp)

            self.kafka_producer.flush()

        return opportunities

    @abstractmethod
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping method - must be implemented by subclasses
        Returns list of raw opportunity dictionaries
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of this scraper's data source"""
        pass
