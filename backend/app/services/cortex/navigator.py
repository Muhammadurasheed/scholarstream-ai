
import asyncio
import structlog
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.crawler_service import crawler_service
from app.services.kafka_config import KafkaConfig, kafka_producer_manager

logger = structlog.get_logger()

class Sentinel:
    """
    Proactive Background Worker (Cortex V2).
    Delegates mission execution to Hunter Drones (UniversalCrawlerService).
    """
    
    """
    COMPREHENSIVE TARGET LIST - All opportunity sources
    These URLs are crawled with Playwright stealth to bypass anti-bot
    """
    TARGETS = [
        # ======== HACKATHONS ========
        "https://devpost.com/hackathons",
        "https://mlh.io/seasons/2025/events",
        "https://dorahacks.io/hackathon",
        "https://angelhack.com/events/",
        "https://www.hackquest.io/hackathon",
        "https://devfolio.co/hackathons",
        "https://hackerearth.com/challenges/",
        
        # ======== BOUNTIES ========
        "https://immunefi.com/explore",
        "https://gitcoin.co/grants-stack/explorer",
        "https://hackerone.com/bug-bounty-programs",
        "https://bugcrowd.com/programs",
        
        # ======== COMPETITIONS ========
        "https://www.kaggle.com/competitions",
        "https://codeforces.com/contests",
        "https://topcoder.com/challenges",
        
        # ======== SCHOLARSHIPS ========
        "https://bold.org/scholarships/",
        "https://www.scholarships.com/financial-aid/college-scholarships/scholarship-directory",
        "https://www.fastweb.com/college-scholarships",
        "https://www.niche.com/colleges/scholarships/",
        "https://www.unigo.com/scholarships/all",
    ]

    async def patrol(self):
        """Deploy Hunter Drones to patrol targets"""
        logger.info("Sentinel deploying Hunter Drones", target_count=len(self.TARGETS))
        try:
            # Delegate to the robust Universal Crawler (Playwright)
            await crawler_service.crawl_and_stream(self.TARGETS, intent="patrol")
        except Exception as e:
            logger.error("Sentinel patrol mission failed", error=str(e))

class Scout:
    """
    Reactive On-Demand Worker.
    Triggered by Chat requests to perform targeted searches via Hunter Drones.
    """
    
    async def execute_mission(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a targeted search mission.
        """
        logger.info("Scout dispatching drone squad", mission=query)
        
        # 1. Generate Search URL (DuckDuckGo or Google)
        search_urls = [
            f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
            f"https://www.google.com/search?q={query.replace(' ', '+')}"
        ]
        
        # 2. Dispatch Drones
        # Note: crawl_and_stream handles browser context and stealth
        try:
            await crawler_service.crawl_and_stream(search_urls, intent="scout_search")
            return [{"url": u, "status": "dispatched"} for u in search_urls]
        except Exception as e:
            logger.error("Scout mission failed", error=str(e))
            return []

# Global Instances
sentinel = Sentinel()
scout = Scout()
