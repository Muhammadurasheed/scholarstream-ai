
import httpx
import asyncio
import structlog
from typing import List, Dict, Any
import time

from app.services.kafka_config import KafkaConfig, kafka_producer_manager

logger = structlog.get_logger()


from playwright.async_api import async_playwright, BrowserContext, Page
import random

class UniversalCrawlerService:
    """
    Universal Crawler Service (Hunter Drones)
    Powered by Playwright for stealth, JS-execution, and dynamic interactions.
    """
    
    def __init__(self):
        self.kafka_initialized = kafka_producer_manager.initialize()
        self.browser = None
        self.playwright = None
        
    async def _init_browser(self):
        """Initialize Playwright Engine if not running"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            # Launch in Headless mode (but defined as non-headless to anti-bots)
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--window-size=1920,1080',
                ]
            )
            
    async def _create_stealth_context(self) -> BrowserContext:
        """Create a new incognito context with advanced stealth overrides"""
        await self._init_browser()
        
        # Rotate user agents for anti-detection
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        # Randomize viewport slightly for fingerprint variance
        viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
            {'width': 1366, 'height': 768},
        ]
        
        context = await self.browser.new_context(
            user_agent=random.choice(user_agents),
            viewport=random.choice(viewports),
            locale='en-US',
            timezone_id=random.choice(['America/New_York', 'America/Los_Angeles', 'Europe/London']),
            color_scheme='light',
            has_touch=False,
            is_mobile=False,
            java_script_enabled=True,
        )
        
        # Advanced stealth scripts
        await context.add_init_script("""
            // Remove webdriver flag
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Override platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            
            // Override hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // Override device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            
            // Remove automation indicators from chrome object
            if (window.chrome) {
                window.chrome.runtime = {};
            }
            
            // Override permissions query
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        return context

    async def crawl_and_stream(self, urls: List[str], intent: str = "general"):
        """
        Deploy Hunter Drones to target URLs.
        Executes JS, waits for hydration, and extracts full DOM.
        """
        logger.info("Deploying Hunter Drones", target_count=len(urls), intent=intent)
        
        context = await self._create_stealth_context()
        
        try:
            for url in urls:
                page = await context.new_page()
                try:
                    # BLOCK RESOURCES to speed up
                    await page.route("**/*", lambda route: route.abort() 
                        if route.request.resource_type in ["image", "media", "font"] 
                        else route.continue_())

                    logger.info("Drone approaching target", url=url)
                    
                    # SMART NAVIGATION
                    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    
                    # SMART WAIT (Hydration Check)
                    try:
                        # Wait for network idle or a specific selector if known
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass # Continue even if network keeps polling
                    
                    # Scroll to trigger lazy loads
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2) # Human pause
                    
                    # EXTRACT
                    content = await page.content()
                    title = await page.title()
                    
                    await self._process_success(url, content, title, intent)
                    
                except Exception as e:
                    logger.error("Drone failed mission", url=url, error=str(e))
                finally:
                    await page.close()
                    await asyncio.sleep(random.uniform(1.0, 3.0)) # Stagger
                    
        finally:
            await context.close()
            
    async def _process_success(self, url: str, html_content: str, title: str, intent: str):
        """Process successful extraction"""
        
        # 1. Clean / Minify HTML (basic) to save bandwidth
        # remove scripts/styles for raw storage if desired, but we keep raw for now
        
        payload = {
            "url": url,
            "title": title,
            "html": html_content[:200000],  # 200KB limit
            "crawled_at": time.time(),
            "source": self._extract_domain(url),
            "intent": intent,
            "agent_type": "HunterDrone-V1"
        }
        
        if self.kafka_initialized:
            success = kafka_producer_manager.publish_to_stream(
                topic=KafkaConfig.TOPIC_RAW_HTML,
                key=url,
                value=payload
            )
            if success:
                logger.info("✅ Drone transmitted payload", url=url, size=len(html_content))
            else:
                logger.error("❌ Transmission jammed (Kafka fail)", url=url)
        else:
             logger.warning("Kafka offline, payload dropped", url=url)

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    
    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

# Global instance
crawler_service = UniversalCrawlerService()

