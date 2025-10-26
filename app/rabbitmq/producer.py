import json
import logging
from typing import Dict, Any, Optional
import pika
from .config import rabbitmq_config
from .setup import RabbitMQSetup

logger = logging.getLogger(__name__)


class RabbitMQProducer:
    """Handles publishing messages to RabbitMQ"""
    
    def __init__(self):
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self.setup = RabbitMQSetup()
    
    def connect(self) -> None:
        """Establish connection to RabbitMQ"""
        try:
            self.connection = self.setup.create_connection()
            self.channel = self.connection.channel()
            logger.info("RabbitMQ producer connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect RabbitMQ producer: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close RabbitMQ connection"""
        if self.channel and not self.channel.is_closed:
            self.channel.close()
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        logger.info("RabbitMQ producer disconnected")
    
    def publish_user_lookup_request(self, phone_or_email: str, request_id: str, group_slug: str) -> bool:
        """
        Publish user lookup request message

        Args:
            phone_or_email: Phone number or email to lookup
            request_id: Unique ID to track the request
            group_slug: Group slug for context

        Returns:
            bool: True if message published successfully, False otherwise
        """
        if not self.connection or self.connection.is_closed:
            self.connect()

        try:
            # Prepare message data
            from datetime import datetime
            message_data = {
                "phone_or_email": phone_or_email,
                "request_id": request_id,
                "group_slug": group_slug,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Publish message
            self.channel.basic_publish(
                exchange=rabbitmq_config.user_lookup_exchange,
                routing_key=rabbitmq_config.user_lookup_request_key,
                body=json.dumps(message_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json',
                    reply_to=rabbitmq_config.user_lookup_response_queue,
                    correlation_id=request_id
                )
            )

            logger.info(f"Published user lookup request: {request_id} for {phone_or_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish user lookup request: {e}")
            return False


# Global producer instance
_rabbitmq_producer: Optional[RabbitMQProducer] = None


def get_rabbitmq_producer() -> RabbitMQProducer:
    """Get or create RabbitMQ producer instance"""
    global _rabbitmq_producer
    if _rabbitmq_producer is None:
        _rabbitmq_producer = RabbitMQProducer()
        _rabbitmq_producer.connect()
    return _rabbitmq_producer


def close_rabbitmq_producer() -> None:
    """Close RabbitMQ producer connection"""
    global _rabbitmq_producer
    if _rabbitmq_producer:
        _rabbitmq_producer.disconnect()
        _rabbitmq_producer = None
