import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.db.database import Base


class PendingMemberRequest(Base):
    """Model to track pending member addition requests"""
    __tablename__ = "pending_member_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    request_id = Column(String, unique=True, index=True, nullable=False)
    group_id = Column(String, nullable=False, index=True)
    phone_or_email = Column(String, nullable=False)
    admin_user_id = Column(String, nullable=False, index=True)
    is_admin = Column(Boolean, default=False)
    status = Column(String, default="pending", index=True)  # pending, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
