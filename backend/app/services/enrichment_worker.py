
import asyncio
import json
import time
from typing import List, Dict, Any
from confluent_kafka import Consumer, KafkaError, Message
import structlog

from app.config import settings
from app.services.kafka_config import KafkaConfig, kafka_producer_manager
from app.services.ai_enrichment_service import ai_enrichment_service

logger = structlog.get_logger()

class EnrichmentWorker:
    """
    AI REQUEST CONSUMER (The "Refinery")
    Consumes RAW HTML from 'raw-html-stream'.
    Extracts structured opportunities using Gemini.
    Publishes to 'enriched-opportunities-stream'.
    """
    
    def __init__(self):
        self.config = KafkaConfig()
        self.consumer_config = self.config.get_consumer_config(group_id="ai-refinery-v1")
        self.running = False
        
    async def start(self):
        """Start the AI processing loop"""
        if not self.consumer_config:
            logger.error("Kafka configuration missing, cannot start worker")
            return
            
        logger.info("Starting AI Refinery Worker...")
        
        # Initialize producer
        if not kafka_producer_manager.initialize():
            logger.error("Failed to initialize producer")
            return
            
        # Initialize consumer
        consumer = Consumer(self.consumer_config)
        consumer.subscribe([KafkaConfig.TOPIC_RAW_HTML])
        
        self.running = True
        logger.info(f"Subscribed to {KafkaConfig.TOPIC_RAW_HTML}")
        logger.info("AI Refinery: READY. Waiting for HTML...")
        
        try:
            while self.running:
                # BATCH COLLECTION
                batch_messages = []
                start_collect = time.time()
                
                # Try to collect 2 messages or wait 2 seconds
                while len(batch_messages) < 2 and (time.time() - start_collect) < 2.0:
                    # CRITICAL: Use asyncio.to_thread to prevent blocking the event loop
                    msg = await asyncio.to_thread(consumer.poll, 0.5)
                    if msg is None:
                        # Yield to event loop
                        await asyncio.sleep(0)
                        continue
                    if msg.error():
                        if msg.error().code() != KafkaError._PARTITION_EOF:
                            logger.error(f"Consumer error: {msg.error()}")
                        continue
                        
                    try:
                        payload = json.loads(msg.value().decode('utf-8'))
                        if payload.get("html") and payload.get("url"):
                            batch_messages.append(payload)
                    except Exception as e:
                        logger.error("Failed to decode message", error=str(e))

                if not batch_messages:
                    # Yield to event loop when idle
                    await asyncio.sleep(0.1)
                    continue

                # PROCESS BATCH
                urls = [m.get("url") for m in batch_messages]
                logger.info(f"🤖 Processing Batch of {len(batch_messages)} pages", urls=urls)
                
                start_time = time.time()
                
                # Extract from batch
                opportunities = await ai_enrichment_service.extract_opportunities_from_html_batch(batch_messages)
                
                duration = time.time() - start_time
                
                if not opportunities:
                    logger.warning(f"⚠️  No opportunities extracted from batch", duration=f"{duration:.2f}s")
                    continue
                    
                logger.info(f"✅ AI Extracted {len(opportunities)} opportunities from batch", duration=f"{duration:.2f}s")

                # PUBLISH RESULTS
                for opp in opportunities:
                    # Resolve source from URL if possible, or use first source
                    # (In batch, we might lose 1-to-1 mapping of which source came from where if not careful,
                    # but opp['url'] should help identify)
                    
                    enriched_message = {
                        'source': "multi-batch", # or find match
                        'enriched_data': opp,
                        'raw_data': {}, 
                        'enriched_at': time.time(),
                        'ai_model': settings.gemini_model,
                        'origin_url': opp.get('url')
                    }
                    
                    kafka_producer_manager.publish_to_stream(
                        topic=KafkaConfig.TOPIC_OPPORTUNITY_ENRICHED,
                        key="ai-refinery",
                        value=enriched_message
                    )
                
                kafka_producer_manager.flush()
                        
        except Exception as e:
            logger.error("Worker connect loop failed", error=str(e))
                    
        except KeyboardInterrupt:
            logger.info("Stopping worker...")
        finally:
            self.close()

    def stop(self):
        """Stop the worker gracefully"""
        self.running = False

    def close(self):
        """Close resources"""
        if self.running: # avoid double close
             logger.info("Closing AI Refinery Worker")
        if hasattr(self, 'consumer_config') and self.consumer_config:
             # actual consumer close is inside the run loop finally block usually
             # but here we just signal stop
             pass
        kafka_producer_manager.close()

# Global instance
enrichment_worker = EnrichmentWorker()

if __name__ == "__main__":
    asyncio.run(enrichment_worker.start())
