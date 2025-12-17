
import structlog
import json
from datetime import datetime
from typing import Optional, List
from app.services.kafka_config import KafkaConfig, kafka_producer_manager
from app.services.cortex.reader_llm import reader_llm
from app.models import OpportunitySchema
from app.config import settings

logger = structlog.get_logger()

class RefineryService:
    """
    The Refinery: Turns Raw Data into Verified Intelligence.
    Consumes: cortex.raw.html.v1
    Produces: opportunity.enriched.v1
    """

    async def process_raw_event(self, key: str, value: dict):
        """
        Process a single raw event from the stream.
        """
        url = value.get("url")
        raw_html = value.get("html")
        source = value.get("source")
        
        logger.info("Refining Raw Event", url=url, source=source)
        
        # 1. Deduplication (Check Firestore Cache - Mocked for speed here, actual impl should query DB)
        # if await self.is_duplicate(url): return

        # 2. Extract Data (Use Reader LLM)
        if not raw_html:
            logger.warning("Empty HTML in raw event", url=url)
            return

        opportunity: Optional[OpportunitySchema] = await reader_llm.parse_opportunity(raw_html, url)
        
        if not opportunity:
            logger.warning("Failed to parse opportunity", url=url)
            return

        # 3. Intelligence Refining
        
        # 3.1 Strict Expiration Gate
        if self._is_expired(opportunity.deadline_timestamp):
            logger.info("Dropped Expired Opportunity", title=opportunity.title, deadline=opportunity.deadline)
            return # DROP EVENT

        # 3.2 Geo-Tagging
        opportunity.geo_tags = self._enrich_geo_tags(opportunity)
        
        # 3.3 Type-Tagging
        opportunity.type_tags = self._enrich_type_tags(opportunity)
        
        # 3.4 Vectorization (The Cortex Memory)
        from app.services.vectorization_service import vectorization_service
        opportunity.embedding = await vectorization_service.vectorize_opportunity(opportunity)

        # 4. publish to Verified Stream
        self._publish_verified(opportunity)

    def _is_expired(self, deadline_ts: int) -> bool:
        """Strict Expiration Logic"""
        if not deadline_ts: return False # Keep if unknown, flag later
        now_ts = int(datetime.now().timestamp())
        return deadline_ts < now_ts

    def _enrich_geo_tags(self, opp: OpportunitySchema) -> List[str]:
        """Auto-detect Global vs Local"""
        tags = set(opp.geo_tags)
        text = (opp.description + " " + str(opp.eligibility_text)).lower()
        
        # Global Indicators
        if any(w in text for w in ["remote", "online", "global", "international", "worldwide"]):
            tags.add("Global")
            
        # Regional Indicators (Example: Nigeria)
        if any(w in text for w in ["nigeria", "lagos", "abuja", "africa"]):
            tags.add("Nigeria")
            
        # Defaults
        if not tags:
            tags.add("Global") # Default to Global if unsure
            
        return list(tags)

    def _enrich_type_tags(self, opp: OpportunitySchema) -> List[str]:
        tags = set(opp.type_tags)
        text = (opp.title + " " + opp.description).lower()
        
        if "hackathon" in text: tags.add("Hackathon")
        if "grant" in text: tags.add("Grant")
        if "scholarship" in text: tags.add("Scholarship")
        if "bounty" in text: tags.add("Bounty")
        
        return list(tags)

    def _publish_verified(self, opp: OpportunitySchema):
        kafka_producer_manager.publish_to_stream(
            topic=KafkaConfig.TOPIC_OPPORTUNITY_ENRICHED,
            key=opp.id, # Hash ID
            value=opp.dict()
        )
        logger.info("✅ Verified Opportunity Published", title=opp.title, tags=opp.geo_tags)

refinery_service = RefineryService()
