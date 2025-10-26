import json
import logging
from typing import Callable, Optional
import pika
from .config import rabbitmq_config
from .setup import RabbitMQSetup

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    """Handles consuming messages from RabbitMQ"""
    
    def __init__(self):
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self.setup = RabbitMQSetup()
    
    def connect(self) -> None:
        """Establish connection to RabbitMQ"""
        try:
            self.connection = self.setup.create_connection()
            self.channel = self.connection.channel()
            
            # Set QoS to process one message at a time
            self.channel.basic_qos(prefetch_count=1)
            
            logger.info("RabbitMQ consumer connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect RabbitMQ consumer: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close RabbitMQ connection"""
        if self.channel and not self.channel.is_closed:
            self.channel.close()
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        logger.info("RabbitMQ consumer disconnected")
    
    def setup_consumer(self, queue_name: str, callback: Callable) -> None:
        """
        Setup consumer for a specific queue
        
        Args:
            queue_name: Name of the queue to consume from
            callback: Function to handle received messages
        """
        if not self.connection or self.connection.is_closed:
            self.connect()
        
        try:
            # Try to declare queue with TTL arguments first
            try:
                self.channel.queue_declare(
                    queue=queue_name,
                    durable=True,
                    exclusive=False,
                    auto_delete=False,
                    arguments={
                        'x-message-ttl': rabbitmq_config.message_ttl
                    }
                )
                logger.info(f"Declared queue with TTL: {queue_name}")
            except Exception as e:
                logger.warning(f"Failed to declare queue {queue_name} with TTL: {e}")
                # Try to declare without arguments if it already exists
                try:
                    self.channel.queue_declare(
                        queue=queue_name,
                        passive=True
                    )
                    logger.info(f"Queue {queue_name} already exists")
                except Exception as e2:
                    logger.error(f"Failed to verify queue {queue_name}: {e2}")
                    raise
            
            # Setup consumer
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=False
            )
            
            logger.info(f"Consumer setup for queue: {queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup consumer for queue {queue_name}: {e}")
            raise
    
    def start_consuming(self) -> None:
        """Start consuming messages"""
        try:
            logger.info("Starting to consume messages...")
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self.stop_consuming()
        except Exception as e:
            logger.error(f"Error while consuming messages: {e}")
            raise
    
    def stop_consuming(self) -> None:
        """Stop consuming messages"""
        if self.channel and not self.channel.is_closed:
            self.channel.stop_consuming()
        logger.info("Stopped consuming messages")


def create_user_lookup_response_callback(handler_func: Callable) -> Callable:
    """
    Create a callback function for processing user lookup response messages
    
    Args:
        handler_func: Function to handle the user lookup response processing
    
    Returns:
        Callback function for RabbitMQ consumer
    """
    def callback(ch, method, properties, body):
        try:
            # Parse message
            message_data = json.loads(body.decode('utf-8'))
            logger.info(f"Received user lookup response: {message_data}")
            
            # Process the message
            success = handler_func(message_data)
            
            if success:
                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info("User lookup response processed successfully")
            else:
                # Reject message and requeue
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                logger.warning("User lookup response processing failed, requeuing")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error processing user lookup response: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    return callback


# Global consumer instance
_rabbitmq_consumer: Optional[RabbitMQConsumer] = None


def get_rabbitmq_consumer() -> RabbitMQConsumer:
    """Get or create RabbitMQ consumer instance"""
    global _rabbitmq_consumer
    if _rabbitmq_consumer is None:
        _rabbitmq_consumer = RabbitMQConsumer()
    return _rabbitmq_consumer


def close_rabbitmq_consumer() -> None:
    """Close RabbitMQ consumer connection"""
    global _rabbitmq_consumer
    if _rabbitmq_consumer:
        _rabbitmq_consumer.disconnect()
        _rabbitmq_consumer = None
