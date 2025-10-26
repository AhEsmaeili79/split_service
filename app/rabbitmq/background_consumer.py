import asyncio
import logging
import threading
from typing import Optional
from app.rabbitmq.consumer import get_rabbitmq_consumer

logger = logging.getLogger(__name__)


class BackgroundConsumerManager:
    """Manages background RabbitMQ consumer processes"""
    
    def __init__(self):
        self.consumer_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.consumer = get_rabbitmq_consumer()
    
    def start_background_consumer(self):
        """Start the background consumer in a separate thread"""
        if self.is_running:
            logger.warning("Background consumer is already running")
            return
        
        self.is_running = True
        self.consumer_thread = threading.Thread(
            target=self._run_consumer,
            daemon=True,
            name="RabbitMQ-Consumer"
        )
        self.consumer_thread.start()
        logger.info("Background RabbitMQ consumer started")
    
    def stop_background_consumer(self):
        """Stop the background consumer"""
        if not self.is_running:
            logger.warning("Background consumer is not running")
            return
        
        self.is_running = False
        
        # Stop consuming messages
        self.consumer.stop_consuming()
        
        # Wait for thread to finish
        if self.consumer_thread and self.consumer_thread.is_alive():
            self.consumer_thread.join(timeout=5)
            if self.consumer_thread.is_alive():
                logger.warning("Consumer thread did not stop gracefully")
        
        # Disconnect from RabbitMQ
        self.consumer.disconnect()
        
        logger.info("Background RabbitMQ consumer stopped")
    
    def _run_consumer(self):
        """Run the consumer in the background thread"""
        try:
            logger.info("Starting background consumer loop")
            
            # Initialize user lookup service consumer setup
            from app.services.user_lookup_service import get_user_lookup_service
            user_lookup_service = get_user_lookup_service()
            user_lookup_service._setup_response_consumer()
            
            while self.is_running:
                try:
                    # Start consuming messages
                    self.consumer.start_consuming()
                except Exception as e:
                    if self.is_running:
                        logger.error(f"Error in consumer loop: {e}")
                        # Wait a bit before retrying
                        import time
                        time.sleep(5)
                    else:
                        logger.info("Consumer loop stopped")
                        break
        except Exception as e:
            logger.error(f"Fatal error in background consumer: {e}")
        finally:
            self.is_running = False
            logger.info("Background consumer thread finished")


# Global background consumer manager
_background_consumer_manager: Optional[BackgroundConsumerManager] = None


def get_background_consumer_manager() -> BackgroundConsumerManager:
    """Get or create background consumer manager instance"""
    global _background_consumer_manager
    if _background_consumer_manager is None:
        _background_consumer_manager = BackgroundConsumerManager()
    return _background_consumer_manager


def start_background_consumer():
    """Start the background consumer"""
    manager = get_background_consumer_manager()
    manager.start_background_consumer()


def stop_background_consumer():
    """Stop the background consumer"""
    manager = get_background_consumer_manager()
    manager.stop_background_consumer()
