import logging
import uuid
from typing import Dict, Any, Optional
from app.rabbitmq.producer import get_rabbitmq_producer
from app.rabbitmq.consumer import get_rabbitmq_consumer, create_user_lookup_response_callback

logger = logging.getLogger(__name__)


class UserLookupService:
    """Service to handle user lookup requests via RabbitMQ"""
    
    def __init__(self):
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.producer = get_rabbitmq_producer()
        self.consumer = get_rabbitmq_consumer()
        self._consumer_setup_completed = False
    
    def _setup_response_consumer(self):
        """Setup consumer for user lookup responses"""
        if self._consumer_setup_completed:
            return
            
        try:
            callback = create_user_lookup_response_callback(self._handle_user_lookup_response)
            self.consumer.setup_consumer("user.lookup.response.queue", callback)
            self._consumer_setup_completed = True
            logger.info("User lookup response consumer setup completed")
        except Exception as e:
            logger.error(f"Failed to setup user lookup response consumer: {e}")
            self._consumer_setup_completed = False
    
    def _handle_user_lookup_response(self, message_data: Dict[str, Any]) -> bool:
        """Handle user lookup response from user service"""
        try:
            request_id = message_data.get("request_id")
            if not request_id:
                logger.error("No request_id in user lookup response")
                return False
            
            logger.info(f"Processing user lookup response for request {request_id}")
            
            # Process the response asynchronously
            self._process_user_lookup_response(request_id, message_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling user lookup response: {e}")
            return False
    
    def _process_user_lookup_response(self, request_id: str, message_data: Dict[str, Any]):
        """Process user lookup response and update group membership"""
        try:
            from app.db.database import SessionLocal
            from app.models.pending_requests import PendingMemberRequest
            from app.services.group_service import add_member_to_group
            
            db = SessionLocal()
            try:
                # Find the pending request
                pending_request = db.query(PendingMemberRequest).filter(
                    PendingMemberRequest.request_id == request_id
                ).first()
                
                if not pending_request:
                    logger.warning(f"No pending request found for request_id: {request_id}")
                    return
                
                if pending_request.status != "pending":
                    logger.warning(f"Request {request_id} is not in pending status")
                    return
                
                # Check if lookup was successful
                if message_data.get("success") and message_data.get("user_data"):
                    user_data = message_data.get("user_data")
                    found_user_id = user_data.get("user_id")
                    
                    if found_user_id:
                        # Add user to group
                        add_member_to_group(
                            db, 
                            pending_request.group_id, 
                            found_user_id, 
                            pending_request.is_admin
                        )
                        
                        # Update pending request status
                        pending_request.status = "completed"
                        db.commit()
                        
                        logger.info(f"Successfully added user {found_user_id} to group {pending_request.group_id}")
                    else:
                        # Invalid user data
                        pending_request.status = "failed"
                        pending_request.error_message = "Invalid user data received"
                        db.commit()
                        logger.error(f"Invalid user data for request {request_id}")
                else:
                    # User not found
                    pending_request.status = "failed"
                    pending_request.error_message = f"User not found with {pending_request.phone_or_email}"
                    db.commit()
                    logger.info(f"User not found for request {request_id}")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing user lookup response for {request_id}: {e}")
            # Try to update the pending request status to failed
            try:
                from app.db.database import SessionLocal
                from app.models.pending_requests import PendingMemberRequest
                
                db = SessionLocal()
                try:
                    pending_request = db.query(PendingMemberRequest).filter(
                        PendingMemberRequest.request_id == request_id
                    ).first()
                    
                    if pending_request:
                        pending_request.status = "failed"
                        pending_request.error_message = f"Processing error: {str(e)}"
                        db.commit()
                finally:
                    db.close()
            except Exception as update_error:
                logger.error(f"Failed to update pending request status: {update_error}")
    
    def lookup_user_by_phone_or_email(self, phone_or_email: str, group_slug: str) -> str:
        """
        Send user lookup request via RabbitMQ
        
        Args:
            phone_or_email: Phone number or email to lookup
            group_slug: Group slug for context
            
        Returns:
            str: Request ID for tracking the response
        """
        # Ensure consumer is set up before sending requests
        self._setup_response_consumer()
        
        request_id = str(uuid.uuid4())
        
        # Store pending request
        self.pending_requests[request_id] = {
            "phone_or_email": phone_or_email,
            "group_slug": group_slug,
            "completed": False,
            "response": None
        }
        
        # Publish lookup request
        success = self.producer.publish_user_lookup_request(
            phone_or_email=phone_or_email,
            request_id=request_id,
            group_slug=group_slug
        )
        
        if not success:
            # Clean up failed request
            del self.pending_requests[request_id]
            raise Exception("Failed to publish user lookup request")
        
        logger.info(f"User lookup request sent: {request_id}")
        return request_id
    
    def get_lookup_result(self, request_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Get the result of a user lookup request (for backward compatibility)
        
        Args:
            request_id: Request ID to check
            timeout: Timeout in seconds
            
        Returns:
            Dict containing user data if found, None otherwise
        """
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if request_id in self.pending_requests:
                request_data = self.pending_requests[request_id]
                
                if request_data["completed"]:
                    response = request_data["response"]
                    # Clean up completed request
                    del self.pending_requests[request_id]
                    
                    if response and response.get("success"):
                        return response.get("user_data")
                    else:
                        return None
                
                time.sleep(0.1)  # Small delay to avoid busy waiting
            else:
                logger.warning(f"Request {request_id} not found")
                return None
        
        # Timeout reached
        logger.warning(f"User lookup request {request_id} timed out")
        if request_id in self.pending_requests:
            del self.pending_requests[request_id]
        return None
    
    def cleanup_old_requests(self, max_age_seconds: int = 300):
        """Clean up old pending requests"""
        import time
        
        current_time = time.time()
        to_remove = []
        
        for request_id, request_data in self.pending_requests.items():
            # Assuming requests older than max_age_seconds should be cleaned up
            if current_time - request_data.get("timestamp", current_time) > max_age_seconds:
                to_remove.append(request_id)
        
        for request_id in to_remove:
            del self.pending_requests[request_id]
            logger.info(f"Cleaned up old request: {request_id}")


# Global service instance
_user_lookup_service: Optional[UserLookupService] = None


def get_user_lookup_service() -> UserLookupService:
    """Get or create user lookup service instance"""
    global _user_lookup_service
    if _user_lookup_service is None:
        _user_lookup_service = UserLookupService()
    return _user_lookup_service
