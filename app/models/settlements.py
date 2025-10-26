import uuid
from sqlalchemy.sql import func
from sqlalchemy import Column, String, DateTime, DECIMAL
from app.db.database import Base


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    group_id = Column(String, nullable=False, index=True)  # Reference to groups
    from_user_id = Column(String, nullable=False, index=True)  # Reference to user service
    to_user_id = Column(String, nullable=False, index=True)  # Reference to user service
    amount = Column(DECIMAL(10, 2), nullable=False)
    settled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
