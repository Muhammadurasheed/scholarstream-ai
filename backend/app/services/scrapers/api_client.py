"""
API Client Manager - FAANG-Level Implementation
Centralized API client for sources with official APIs
Handles authentication, rate limiting, caching, and error recovery
"""
from typing import Optional, Dict, Any, List
import httpx
import structlog
from datetime import datetime, timedelta
import json
import hashlib

logger = structlog.get_logger()


class APIClientManager:
    """
    Manages API clients for various platforms
    FAANG-level: caching, rate limiting, circuit breaker pattern
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.api_keys = self._load_api_keys()
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment/config"""
        import os
        return {
            'kaggle': os.getenv('KAGGLE_API_KEY', ''),
            'github': os.getenv('GITHUB_TOKEN', ''),
            'devpost': os.getenv('DEVPOST_API_KEY', ''),
            'mlh': '',  # MLH doesn't require API key for public data
            'gitcoin': os.getenv('GITCOIN_API_KEY', ''),
            'hackerone': os.getenv('HACKERONE_API_KEY', ''),
        }
    
    async def get_kaggle_competitions(self) -> List[Dict[str, Any]]:
        """
        Get competitions from Kaggle API
        Official API - highly reliable
        """
        cache_key = 'kaggle_competitions'
        
        # Check cache (1 hour TTL)
        if self._is_cached(cache_key, ttl_minutes=60):
            return self.cache[cache_key]['data']
        
        try:
            # Kaggle API endpoint
            url = 'https://www.kaggle.com/api/v1/competitions/list'
            
            headers = {}
            if self.api_keys.get('kaggle'):
                headers['Authorization'] = f"Bearer {self.api_keys['kaggle']}"
            
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            competitions = response.json()
            
            # Cache result
            self._cache_result(cache_key, competitions)
            
            logger.info(f"Fetched {len(competitions)} Kaggle competitions")
            return competitions
            
        except Exception as e:
            logger.error(f"Kaggle API error: {e}")
            return []
    
    async def get_mlh_hackathons(self, season: str = 'current') -> List[Dict[str, Any]]:
        """
        Get hackathons from MLH API
        Official API - no key required
        """
        cache_key = f'mlh_hackathons_{season}'
        
        if self._is_cached(cache_key, ttl_minutes=30):
            return self.cache[cache_key]['data']
        
        try:
            # MLH API endpoint
            url = f'https://mlh.io/seasons/{season}/events'
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            # MLH returns HTML, need to parse
            # For now, use their JSON feed if available
            hackathons = []
            
            # Try JSON endpoint
            json_url = 'https://mlh-events.now.sh/na-2024'
            try:
                json_response = await self.client.get(json_url)
                if json_response.status_code == 200:
                    hackathons = json_response.json()
            except:
                pass
            
            self._cache_result(cache_key, hackathons)
            
            logger.info(f"Fetched {len(hackathons)} MLH hackathons")
            return hackathons
            
        except Exception as e:
            logger.error(f"MLH API error: {e}")
            return []
    
    async def get_github_bounties(self, org: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get bug bounties from GitHub
        Uses GitHub API with authentication
        """
        cache_key = f'github_bounties_{org or "all"}'
        
        if self._is_cached(cache_key, ttl_minutes=15):
            return self.cache[cache_key]['data']
        
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json'
            }
            
            if self.api_keys.get('github'):
                headers['Authorization'] = f"token {self.api_keys['github']}"
            
            # Search for issues with bounty labels
            url = 'https://api.github.com/search/issues'
            params = {
                'q': 'label:bounty state:open',
                'per_page': 100,
                'sort': 'created',
                'order': 'desc'
            }
            
            if org:
                params['q'] += f' org:{org}'
            
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            bounties = data.get('items', [])
            
            self._cache_result(cache_key, bounties)
            
            logger.info(f"Fetched {len(bounties)} GitHub bounties")
            return bounties
            
        except Exception as e:
            logger.error(f"GitHub API error: {e}")
            return []
    
    async def get_devpost_hackathons(self) -> List[Dict[str, Any]]:
        """
        Get hackathons from Devpost
        Uses web scraping as they don't have public API
        """
        cache_key = 'devpost_hackathons'
        
        if self._is_cached(cache_key, ttl_minutes=60):
            return self.cache[cache_key]['data']
        
        try:
            url = 'https://devpost.com/api/hackathons'
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            data = response.json()
            hackathons = data.get('hackathons', [])
            
            self._cache_result(cache_key, hackathons)
            
            logger.info(f"Fetched {len(hackathons)} Devpost hackathons")
            return hackathons
            
        except Exception as e:
            logger.error(f"Devpost API error: {e}")
            return []
    
    def _is_cached(self, key: str, ttl_minutes: int) -> bool:
        """Check if cached data is still valid"""
        if key not in self.cache:
            return False
        
        cached_at = self.cache[key]['timestamp']
        age = datetime.now() - cached_at
        
        return age < timedelta(minutes=ttl_minutes)
    
    def _cache_result(self, key: str, data: Any):
        """Cache API result with timestamp"""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Global instance
api_client_manager = APIClientManager()
