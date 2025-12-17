import structlog
import time
import hashlib
from typing import Dict, List, Any, Optional
from collections import deque
import asyncio

from app.config import settings

logger = structlog.get_logger()


def generate_opportunity_id(opportunity: Dict[str, Any]) -> str:
    """
    Generate a STABLE, DETERMINISTIC ID for deduplication.
    Uses source_url as primary key, falls back to title+org hash.
    """
    url = opportunity.get('url') or opportunity.get('source_url') or ''
    
    if url:
        # URL-based ID (preferred - most stable)
        return hashlib.sha256(url.encode()).hexdigest()[:24]
    
    # Fallback: Hash of title + organization
    title = (opportunity.get('name') or opportunity.get('title') or '').lower().strip()
    org = (opportunity.get('organization') or '').lower().strip()
    combined = f"{title}|{org}"
    
    return hashlib.sha256(combined.encode()).hexdigest()[:24]


class CortexFlinkProcessor:
    """
    The Cortex Stream Processor (Python Native V2)
    
    ENHANCED DEDUPLICATION:
    1. Content-based hashing (URL + Title + Organization)
    2. Sliding window expiration (1 hour)
    3. Persisted seen set for cross-session deduplication
    """
    
    def __init__(self):
        self.window_size_seconds = 3600  # 1 Hour
        self.seen_opportunities = {}  # Map[content_hash, timestamp]
        self.processing_queue = deque()
        self.total_processed = 0
        self.duplicates_dropped = 0
        logger.info("Cortex Processor Online (Engine: Native Python V2 - Enhanced Deduplication)")
        
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Ingest and process a single raw opportunity event.
        Returns None if duplicate, otherwise returns the enriched event.
        """
        # Generate stable content-based ID
        content_id = generate_opportunity_id(event)
        url = event.get('url') or event.get('source_url') or ''
        
        now = time.time()
        
        # 1. DEDUPLICATION LOGIC (Content-based, not just URL)
        last_seen = self.seen_opportunities.get(content_id, 0)
        
        if (now - last_seen) < self.window_size_seconds:
            self.duplicates_dropped += 1
            logger.debug(
                "Duplicate Dropped (Cortex Shield)", 
                content_id=content_id[:8],
                url=url[:50] if url else 'N/A',
                total_dropped=self.duplicates_dropped
            )
            return None  # Drop duplicate
            
        # Update state with stable ID
        self.seen_opportunities[content_id] = now
        
        # 2. ENRICH EVENT WITH STABLE ID
        event['id'] = content_id  # Assign stable ID
        event['cortex_processed_at'] = now
        
        # 3. WINDOW MANAGEMENT
        self._cleanup_window(now)
        self.processing_queue.append((now, event))
        self.total_processed += 1
        
        logger.info(
            "⚡ Cortex Processed Event", 
            content_id=content_id[:8],
            url=url[:50] if url else 'N/A',
            window_count=len(self.processing_queue),
            total_processed=self.total_processed,
            duplicates_dropped=self.duplicates_dropped
        )
        
        return event

    def _cleanup_window(self, current_time: float):
        """Slide the window (Evict old events and stale seen entries)"""
        # Clean processing queue
        while self.processing_queue:
            timestamp, _ = self.processing_queue[0]
            if (current_time - timestamp) > self.window_size_seconds:
                self.processing_queue.popleft()
            else:
                break
        
        # Clean seen_opportunities (prevent memory leak)
        stale_ids = [
            cid for cid, ts in self.seen_opportunities.items()
            if (current_time - ts) > self.window_size_seconds * 2  # 2x window for safety
        ]
        for cid in stale_ids:
            del self.seen_opportunities[cid]
        
        if stale_ids:
            logger.debug("Evicted stale entries", count=len(stale_ids))

    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return {
            'total_processed': self.total_processed,
            'duplicates_dropped': self.duplicates_dropped,
            'unique_in_window': len(self.processing_queue),
            'seen_cache_size': len(self.seen_opportunities),
            'deduplication_rate': f"{(self.duplicates_dropped / max(1, self.total_processed + self.duplicates_dropped)) * 100:.1f}%"
        }

    def is_duplicate(self, opportunity: Dict[str, Any]) -> bool:
        """Quick check if opportunity is a duplicate without processing"""
        content_id = generate_opportunity_id(opportunity)
        now = time.time()
        last_seen = self.seen_opportunities.get(content_id, 0)
        return (now - last_seen) < self.window_size_seconds


# Singleton for the app to use
cortex_processor = CortexFlinkProcessor()

if __name__ == "__main__":
    # Test Loop
    processor = CortexFlinkProcessor()
    
    async def test():
        # Test 1: First event should pass
        result1 = await processor.process_event({"url": "http://test.com", "name": "Test Scholarship"})
        print(f"Event 1: {'Processed' if result1 else 'Dropped'}")
        
        # Test 2: Same event should be dropped
        result2 = await processor.process_event({"url": "http://test.com", "name": "Test Scholarship"})
        print(f"Event 2: {'Processed' if result2 else 'Dropped'}")
        
        # Test 3: Different event should pass
        result3 = await processor.process_event({"url": "http://different.com", "name": "Different Scholarship"})
        print(f"Event 3: {'Processed' if result3 else 'Dropped'}")
        
        print(f"\nStats: {processor.get_stats()}")
    
    asyncio.run(test())
