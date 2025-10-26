import logging
import threading
import time
from typing import Optional
from app.db.database import SessionLocal
from app.models.pending_requests import PendingMemberRequest

logger = logging.getLogger(__name__)


class PendingRequestCleanupManager:
    """Manages cleanup of old pending requests"""
    
    def __init__(self):
        self.cleanup_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.cleanup_interval = 300  # 5 minutes
    
    def start_cleanup(self):
        """Start the cleanup process in a separate thread"""
        if self.is_running:
            logger.warning("Cleanup process is already running")
            return
        
        self.is_running = True
        self.cleanup_thread = threading.Thread(
            target=self._run_cleanup,
            daemon=True,
            name="PendingRequest-Cleanup"
        )
        self.cleanup_thread.start()
        logger.info("Pending request cleanup process started")
    
    def stop_cleanup(self):
        """Stop the cleanup process"""
        if not self.is_running:
            logger.warning("Cleanup process is not running")
            return
        
        self.is_running = False
        
        # Wait for thread to finish
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
            if self.cleanup_thread.is_alive():
                logger.warning("Cleanup thread did not stop gracefully")
        
        logger.info("Pending request cleanup process stopped")
    
    def _run_cleanup(self):
        """Run the cleanup process in the background thread"""
        try:
            logger.info("Starting pending request cleanup loop")
            while self.is_running:
                try:
                    self._cleanup_old_requests()
                    # Wait for the next cleanup cycle
                    time.sleep(self.cleanup_interval)
                except Exception as e:
                    if self.is_running:
                        logger.error(f"Error in cleanup loop: {e}")
                        # Wait a bit before retrying
                        time.sleep(60)
                    else:
                        logger.info("Cleanup loop stopped")
                        break
        except Exception as e:
            logger.error(f"Fatal error in cleanup process: {e}")
        finally:
            self.is_running = False
            logger.info("Cleanup thread finished")
    
    def _cleanup_old_requests(self):
        """Clean up old pending requests"""
        try:
            db = SessionLocal()
            try:
                # Clean up requests older than 1 hour
                from datetime import datetime, timedelta
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                
                old_requests = db.query(PendingMemberRequest).filter(
                    PendingMemberRequest.created_at < cutoff_time,
                    PendingMemberRequest.status == "pending"
                ).all()
                
                if old_requests:
                    for request in old_requests:
                        request.status = "failed"
                        request.error_message = "Request timed out"
                    
                    db.commit()
                    logger.info(f"Cleaned up {len(old_requests)} old pending requests")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error cleaning up old requests: {e}")


# Global cleanup manager
_cleanup_manager: Optional[PendingRequestCleanupManager] = None


def get_cleanup_manager() -> PendingRequestCleanupManager:
    """Get or create cleanup manager instance"""
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = PendingRequestCleanupManager()
    return _cleanup_manager


def start_pending_request_cleanup():
    """Start the pending request cleanup process"""
    manager = get_cleanup_manager()
    manager.start_cleanup()


def stop_pending_request_cleanup():
    """Stop the pending request cleanup process"""
    manager = get_cleanup_manager()
    manager.stop_cleanup()
