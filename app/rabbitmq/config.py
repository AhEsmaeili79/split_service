import os
from typing import Optional
from pydantic_settings import BaseSettings


class RabbitMQConfig(BaseSettings):
    """RabbitMQ configuration settings"""
    
    # Connection settings
    host: str = os.getenv("RABBITMQ_HOST")
    port: int = int(os.getenv("RABBITMQ_PORT"))
    username: str = os.getenv("RABBITMQ_USERNAME")
    password: str = os.getenv("RABBITMQ_PASSWORD")
    virtual_host: str = os.getenv("RABBITMQ_VHOST")
    
    # Connection pool settings
    connection_attempts: int = int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", "3"))
    retry_delay: float = float(os.getenv("RABBITMQ_RETRY_DELAY", "2.0"))
    heartbeat: int = int(os.getenv("RABBITMQ_HEARTBEAT", "600"))
    
    # Exchange settings
    user_lookup_exchange: str = "user.lookup.exchange"
    exchange_type: str = "topic"
    
    # Queue settings
    user_lookup_queue: str = "user.lookup.request.queue"
    user_lookup_response_queue: str = "user.lookup.response.queue"
    
    # Routing keys
    user_lookup_request_key: str = "user.lookup.request"
    user_lookup_response_key: str = "user.lookup.response"
    
    # Message settings
    message_ttl: int = int(os.getenv("RABBITMQ_MESSAGE_TTL", "300000"))  # 5 minutes in milliseconds
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
rabbitmq_config = RabbitMQConfig()
