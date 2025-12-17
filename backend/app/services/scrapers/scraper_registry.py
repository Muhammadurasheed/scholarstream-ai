"""
Scraper Registry - Central hub for all opportunity scrapers
Manages multiple sources with health monitoring and intelligent scheduling
"""
from typing import List, Dict, Any, Type
from datetime import datetime, timedelta
import structlog
import asyncio

from .base_scraper import BaseScraper
from .devpost_scraper import DevpostScraper
from .mlh_scraper import MLHScraper
from .web3_bounties_scraper import Web3BountiesScraper
from .kaggle_scraper import KaggleScraper
from .scholarships_scraper import ScholarshipsScraper

logger = structlog.get_logger()


class ScraperRegistry:
    """Manages all scrapers with health monitoring"""
    
    def __init__(self):
        self.scrapers: Dict[str, BaseScraper] = {}
        self.health_status: Dict[str, Dict[str, Any]] = {}
        self._register_all_scrapers()
    
    def _register_all_scrapers(self):
        """Register all available scrapers"""
        # DISABLED FOR PIVOT TO UNIVERSAL CRAWLER
        # self.register(DevpostScraper())
        # self.register(MLHScraper())
        # self.register(Web3BountiesScraper())
        # self.register(KaggleScraper())
        # self.register(ScholarshipsScraper())
        
        # try:
        #     from .scholarships.fastweb_scraper import FastwebScraper
        #     self.register(FastwebScraper())
        # except ImportError as e:
        #     logger.error(f"Failed to import FastwebScraper: {e}")
        
        logger.info(f"Universal Crawler Mode: Legacy Scrapers Disabled")
    
    def register(self, scraper: BaseScraper):
        """Register a scraper with health monitoring"""
        name = scraper.get_source_name()
        self.scrapers[name] = scraper
        self.health_status[name] = {
            'last_success': None,
            'last_failure': None,
            'success_count': 0,
            'failure_count': 0,
            'avg_response_time': 0,
            'is_healthy': True,
            'last_opportunity_count': 0
        }
    
    async def scrape_all(self, user_profile: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Scrape from ALL sources in parallel with intelligent batching
        Returns unified list of opportunities
        """
        logger.info("Starting comprehensive scraping from all sources")
        
        # Batch scrapers to avoid overwhelming network
        batch_size = 3  # Process 3 scrapers at a time
        all_opportunities = []
        
        scraper_list = list(self.scrapers.items())
        for i in range(0, len(scraper_list), batch_size):
            batch = scraper_list[i:i+batch_size]
            
            tasks = []
            for name, scraper in batch:
                tasks.append(self._scrape_with_monitoring(name, scraper))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_opportunities.extend(result)
            
            # Brief pause between batches to be respectful
            if i + batch_size < len(scraper_list):
                await asyncio.sleep(0.5)
        
        logger.info(
            "Comprehensive scraping complete",
            total_opportunities=len(all_opportunities),
            total_sources=len(self.scrapers)
        )
        
        return all_opportunities
    
    async def _scrape_with_monitoring(self, name: str, scraper: BaseScraper) -> List[Dict[str, Any]]:
        """Scrape with health monitoring and error handling"""
        start_time = datetime.now()
        
        try:
            opportunities = await scraper.scrape()
            
            # Update health status
            self.health_status[name]['last_success'] = datetime.now()
            self.health_status[name]['success_count'] += 1
            self.health_status[name]['is_healthy'] = True
            self.health_status[name]['last_opportunity_count'] = len(opportunities)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Update average response time
            prev_avg = self.health_status[name]['avg_response_time']
            success_count = self.health_status[name]['success_count']
            self.health_status[name]['avg_response_time'] = (
                (prev_avg * (success_count - 1) + elapsed) / success_count
            )
            
            logger.info(
                f"{name} scraper succeeded",
                count=len(opportunities),
                time=f"{elapsed:.2f}s"
            )
            
            return opportunities
            
        except Exception as e:
            # Update health status
            self.health_status[name]['last_failure'] = datetime.now()
            self.health_status[name]['failure_count'] += 1
            
            # Mark as unhealthy if 3+ consecutive failures
            if self.health_status[name]['failure_count'] >= 3:
                self.health_status[name]['is_healthy'] = False
            
            logger.error(f"{name} scraper failed", error=str(e))
            
            return []
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get health status of all scrapers"""
        healthy = sum(1 for status in self.health_status.values() if status['is_healthy'])
        total = len(self.scrapers)
        
        total_opportunities = sum(
            status['last_opportunity_count'] 
            for status in self.health_status.values()
        )
        
        return {
            'total_scrapers': total,
            'healthy_scrapers': healthy,
            'unhealthy_scrapers': total - healthy,
            'health_percentage': (healthy / total * 100) if total > 0 else 0,
            'total_opportunities_last_run': total_opportunities,
            'scraper_details': self.health_status
        }
    
    def get_scraper_names(self) -> List[str]:
        """Get list of all registered scraper names"""
        return list(self.scrapers.keys())


# Global registry instance
scraper_registry = ScraperRegistry()
