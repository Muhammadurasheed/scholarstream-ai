"""
Multi-Opportunity Discovery Service
Real-time scraping for scholarships, hackathons, bounties, competitions
Uses APIs and web scraping with AI enrichment
"""
import httpx
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
import structlog
from datetime import datetime, timedelta
import asyncio
import json
import random

from app.models import ScrapedScholarship
from app.config import settings
from app.services.scrapers.scraper_registry import scraper_registry

logger = structlog.get_logger()


class OpportunityScraperService:
    """Web scraper for discovering scholarships"""
    
    def __init__(self):
        """Initialize scraper with HTTP client and registry"""
        self.client = httpx.AsyncClient(
            timeout=30.0,
        )
        self.registry = scraper_registry

    async def discover_all_opportunities(self, user_profile: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Discover opportunities using all registered scrapers"""
        if user_profile is None:
            user_profile = {}
            
        logger.info("Starting COMPREHENSIVE multi-opportunity discovery")
        
        # DISABLE LEGACY SCRAPING
        return []

        # Use registry to scrape all sources in parallel
        # all_opportunities = await self.registry.scrape_all(user_profile)
        
        # Validate URLs to ensure apply links work
        logger.info("Validating opportunity URLs")
        validated_opportunities = await self._validate_urls(all_opportunities)
        
        # Deduplicate
        unique_opportunities = self._deduplicate(validated_opportunities)
        
        # Get health report
        health_report = self.registry.get_health_report()
        
        # Count by type
        type_counts = {
            'scholarship': len([o for o in unique_opportunities if o.get('type') == 'scholarship']),
            'hackathon': len([o for o in unique_opportunities if o.get('type') == 'hackathon']),
            'bounty': len([o for o in unique_opportunities if o.get('type') == 'bounty']),
            'competition': len([o for o in unique_opportunities if o.get('type') == 'competition']),
        }
        
        logger.info(
            "Discovery complete",
            total_scraped=len(all_opportunities),
            after_validation=len(validated_opportunities),
            unique=len(unique_opportunities),
            healthy_scrapers=health_report['healthy_scrapers'],
            total_scrapers=health_report['total_scrapers'],
            **type_counts
        )
        
        return unique_opportunities
    
    async def _validate_urls(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate that source URLs are accessible
        Adds url_validated flag to each opportunity
        """
        validated = []
        
        # Validate in batches to avoid overwhelming network
        batch_size = 10
        for i in range(0, len(opportunities), batch_size):
            batch = opportunities[i:i+batch_size]
            tasks = []
            
            for opp in batch:
                url = opp.get('url') or opp.get('source_url')
                if url:
                    tasks.append(self._validate_single_url(url, opp))
                else:
                    # No URL, mark as unvalidated
                    opp['source_url'] = ''
                    opp['url_validated'] = False
                    validated.append(opp)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            validated.extend([r for r in results if isinstance(r, dict)])
            
            # Brief pause between batches
            if i + batch_size < len(opportunities):
                await asyncio.sleep(0.2)
        
        logger.info(
            "URL validation complete",
            total=len(opportunities),
            validated=len([o for o in validated if o.get('url_validated')])
        )
        
        return validated
    
    async def _validate_single_url(self, url: str, opp: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single URL"""
        try:
            # Quick HEAD request to check if URL is valid
            response = await self.client.head(url, timeout=5.0)
            
            if response.status_code < 400:
                opp['source_url'] = url
                opp['url_validated'] = True
            else:
                logger.warning(f"Invalid URL {url}: {response.status_code}")
                opp['source_url'] = url
                opp['url_validated'] = False
                
        except Exception as e:
            logger.debug(f"URL validation failed for {url}: {e}")
            # Still include but mark as unvalidated
            opp['source_url'] = url
            opp['url_validated'] = False
        
        return opp
    
    def _deduplicate(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates based on name and organization"""
        seen = set()
        unique = []
        
        for opp in opportunities:
            key = f"{opp.get('name', '').lower()}_{opp.get('organization', '').lower()}"
            if key not in seen:
                seen.add(key)
                unique.append(opp)
        
        return unique
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Global scraper service instance
scraper_service = OpportunityScraperService()
