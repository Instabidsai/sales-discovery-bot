"""Background worker for async tasks (optional).

This agent is primarily API-driven, but this worker can handle:
- Batch conversation analysis
- Lead follow-ups
- Metrics aggregation
"""

import asyncio
import os
import signal
import logging
from datetime import datetime, timedelta

import redis.asyncio as redis
from opentelemetry import trace

from agent.config import get_config
from api.database import DatabaseManager

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class BackgroundWorker:
    """Optional background worker for async tasks."""
    
    def __init__(self):
        self.config = get_config()
        self.redis_client = None
        self.db = None
        self.running = True
        
        # Graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def initialize(self):
        """Initialize connections."""
        self.redis_client = redis.from_url(self.config.redis_url)
        self.db = DatabaseManager(self.config.postgres_dsn)
        await self.db.initialize()
    
    async def cleanup(self):
        """Cleanup connections."""
        if self.redis_client:
            await self.redis_client.close()
        if self.db:
            await self.db.close()
    
    async def aggregate_metrics(self):
        """Aggregate conversation metrics hourly."""
        with tracer.start_as_current_span("aggregate_metrics"):
            # This is a placeholder for metrics aggregation
            # In production, this would calculate:
            # - Conversations per hour
            # - Average time to proposal
            # - Conversion rates
            # - Partnership tier distribution
            
            logger.info("Aggregating metrics...")
            # Implementation would go here
            pass
    
    async def check_abandoned_conversations(self):
        """Check for conversations that stalled."""
        with tracer.start_as_current_span("check_abandoned"):
            # Find conversations with no activity for > 30 minutes
            # Could send follow-up emails or notifications
            
            logger.info("Checking abandoned conversations...")
            # Implementation would go here
            pass
    
    async def run(self):
        """Main worker loop."""
        await self.initialize()
        
        logger.info("Background worker started")
        
        last_metrics_run = datetime.utcnow()
        last_abandoned_check = datetime.utcnow()
        
        while self.running:
            try:
                now = datetime.utcnow()
                
                # Run metrics aggregation hourly
                if now - last_metrics_run > timedelta(hours=1):
                    await self.aggregate_metrics()
                    last_metrics_run = now
                
                # Check abandoned conversations every 30 minutes
                if now - last_abandoned_check > timedelta(minutes=30):
                    await self.check_abandoned_conversations()
                    last_abandoned_check = now
                
                # Sleep for a bit
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                await asyncio.sleep(5)  # Brief pause on error
        
        await self.cleanup()
        logger.info("Background worker shutdown complete")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run worker
    worker = BackgroundWorker()
    asyncio.run(worker.run())