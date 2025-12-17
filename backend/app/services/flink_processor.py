import structlog
import time
from typing import Dict, List, Any
from collections import deque
import asyncio

from app.config import settings
# from pyflink.datastream import StreamExecutionEnvironment (Unavailable on specific Windows envs)

logger = structlog.get_logger()

class CortexFlinkProcessor:
    """
    The Cortex Stream Processor (Python Native V1)
    
    Architecture Note:
    Normally this would use Apache Flink for distributed state management.
    Due to local environment constraints (Windows build tools for Flink),
    we are using a Python-native 'Micro-Batch' processor that mimics Flink's logic.
    
    Capabilities:
    1. Stateful Deduplication (1 Hour Window)
    2. Stream Aggregation
    """
    
    def __init__(self):
        self.window_size_seconds = 3600  # 1 Hour
        self.seen_urls = {}  # Map[url, timestamp]
        self.processing_queue = deque()
        logger.info("Cortex Processor Online (Engine: Native Python)")
        
    async def process_event(self, event: Dict[str, Any]):
        """
        Ingest and process a single raw opportunity event
        Mimics Flink's `SELECT * FROM stream`
        """
        url = event.get('url')
        if not url: return

        now = time.time()
        
        # 1. DEDUPLICATION LOGIC
        # Logic: ROW_NUMBER() OVER (PARTITION BY url ORDER BY crawled_at DESC)
        last_seen = self.seen_urls.get(url, 0)
        
        if (now - last_seen) < self.window_size_seconds:
            logger.debug("Duplicate Dropped (Cortex Shield)", url=url)
            return # Drop duplicate
            
        # Update state
        self.seen_urls[url] = now
        
        # 2. ENRICHMENT / PROCESSING
        # Clean up the deque (Expired windows)
        self._cleanup_window(now)
        
        # Add to window
        self.processing_queue.append((now, event))
        
        # Log success
        logger.info(
            "⚡ Cortex Processed Event", 
            url=url, 
            window_count=len(self.processing_queue)
        )
        
        # In a real Flink setup, we'd emit to a Sink here.
        # For now, we assume the successful return implies "Flow continues".
        return event

    def _cleanup_window(self, current_time: float):
        """Slide the window (Evict old events)"""
        while self.processing_queue:
            timestamp, _ = self.processing_queue[0]
            if (current_time - timestamp) > self.window_size_seconds:
                self.processing_queue.popleft()
            else:
                break

# Singleton for the app to use
cortex_processor = CortexFlinkProcessor()

if __name__ == "__main__":
    # Test Loop
    processor = CortexFlinkProcessor()
    asyncio.run(processor.process_event({"url": "http://test.com", "crawled_at": time.time()}))
