import logging
import pika
from typing import Optional
from .config import rabbitmq_config

logger = logging.getLogger(__name__)


class RabbitMQSetup:
    """Handles RabbitMQ exchange, queue, and binding setup"""
    
    def __init__(self, connection: Optional[pika.BlockingConnection] = None):
        self.connection = connection
        self.channel = None
    
    def create_connection(self) -> pika.BlockingConnection:
        """Create a new RabbitMQ connection"""
        try:
            credentials = pika.PlainCredentials(
                rabbitmq_config.username, 
                rabbitmq_config.password
            )
            
            parameters = pika.ConnectionParameters(
                host=rabbitmq_config.host,
                port=rabbitmq_config.port,
                virtual_host=rabbitmq_config.virtual_host,
                credentials=credentials,
                heartbeat=rabbitmq_config.heartbeat,
                connection_attempts=rabbitmq_config.connection_attempts,
                retry_delay=rabbitmq_config.retry_delay
            )
            
            connection = pika.BlockingConnection(parameters)
            logger.info(f"Connected to RabbitMQ at {rabbitmq_config.host}:{rabbitmq_config.port}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def setup_exchanges_and_queues(self) -> None:
        """Create exchanges, queues, and bindings"""
        if not self.connection:
            self.connection = self.create_connection()
        
        self.channel = self.connection.channel()
        
        try:
            # Declare the user lookup exchange
            self.channel.exchange_declare(
                exchange=rabbitmq_config.user_lookup_exchange,
                exchange_type=rabbitmq_config.exchange_type,
                durable=True,
                auto_delete=False
            )
            logger.info(f"Declared exchange: {rabbitmq_config.user_lookup_exchange}")
            
            # Declare user lookup request queue
            try:
                self.channel.queue_declare(
                    queue=rabbitmq_config.user_lookup_queue,
                    durable=True,
                    exclusive=False,
                    auto_delete=False,
                    arguments={
                        'x-message-ttl': rabbitmq_config.message_ttl
                    },
                    passive=False
                )
                logger.info(f"Declared queue: {rabbitmq_config.user_lookup_queue}")
            except Exception as e:
                logger.warning(f"Queue {rabbitmq_config.user_lookup_queue} declaration failed: {e}")
                # Try to declare without arguments if it already exists
                try:
                    self.channel.queue_declare(
                        queue=rabbitmq_config.user_lookup_queue,
                        passive=True
                    )
                    logger.info(f"Queue {rabbitmq_config.user_lookup_queue} already exists")
                except Exception as e2:
                    logger.error(f"Failed to verify queue {rabbitmq_config.user_lookup_queue}: {e2}")
            
            # Declare user lookup response queue
            try:
                self.channel.queue_declare(
                    queue=rabbitmq_config.user_lookup_response_queue,
                    durable=True,
                    exclusive=False,
                    auto_delete=False,
                    arguments={
                        'x-message-ttl': rabbitmq_config.message_ttl
                    },
                    passive=False
                )
                logger.info(f"Declared queue: {rabbitmq_config.user_lookup_response_queue}")
            except Exception as e:
                logger.warning(f"Queue {rabbitmq_config.user_lookup_response_queue} declaration failed: {e}")
                # Try to declare without arguments if it already exists
                try:
                    self.channel.queue_declare(
                        queue=rabbitmq_config.user_lookup_response_queue,
                        passive=True
                    )
                    logger.info(f"Queue {rabbitmq_config.user_lookup_response_queue} already exists")
                except Exception as e2:
                    logger.error(f"Failed to verify queue {rabbitmq_config.user_lookup_response_queue}: {e2}")
            
            # Bind user lookup request queue to exchange
            self.channel.queue_bind(
                exchange=rabbitmq_config.user_lookup_exchange,
                queue=rabbitmq_config.user_lookup_queue,
                routing_key=rabbitmq_config.user_lookup_request_key
            )
            logger.info(f"Bound {rabbitmq_config.user_lookup_queue} to {rabbitmq_config.user_lookup_exchange} with key {rabbitmq_config.user_lookup_request_key}")
            
            # Bind user lookup response queue to exchange
            self.channel.queue_bind(
                exchange=rabbitmq_config.user_lookup_exchange,
                queue=rabbitmq_config.user_lookup_response_queue,
                routing_key=rabbitmq_config.user_lookup_response_key
            )
            logger.info(f"Bound {rabbitmq_config.user_lookup_response_queue} to {rabbitmq_config.user_lookup_exchange} with key {rabbitmq_config.user_lookup_response_key}")
            
        except Exception as e:
            logger.error(f"Failed to setup RabbitMQ exchanges and queues: {e}")
            raise
    
    def close_connection(self) -> None:
        """Close the RabbitMQ connection"""
        if self.channel and not self.channel.is_closed:
            self.channel.close()
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        logger.info("RabbitMQ connection closed")


def setup_rabbitmq() -> None:
    """Initialize RabbitMQ setup"""
    setup = RabbitMQSetup()
    try:
        setup.setup_exchanges_and_queues()
        logger.info("RabbitMQ setup completed successfully")
    finally:
        setup.close_connection()


# Initialize RabbitMQ (optional)
def init_rabbitmq():
    """Initialize RabbitMQ connection and setup"""
    logger.info("Starting RabbitMQ initialization...")
    try:
        setup_rabbitmq()
        logger.info("RabbitMQ setup completed successfully")
    except Exception as e:
        logger.error(f"Failed to setup RabbitMQ: {e}")
        logger.warning("Application will continue without RabbitMQ functionality")
