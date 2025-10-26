import uuid
from sqlalchemy.sql import func
from sqlalchemy import Column, String, DateTime, DECIMAL, Text, Boolean
from app.db.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    group_id = Column(String, nullable=False, index=True)  # Reference to groups (no FK constraint)
    group_category_id = Column(String, nullable=False)  # Reference to group_categories
    title = Column(String(200), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    paid_by = Column(String, nullable=False, index=True)  # Reference to user service
    description = Column(Text, nullable=True)
    receipt_url = Column(String, nullable=True)
    date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class ExpenseShare(Base):
    __tablename__ = "expense_shares"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    expense_id = Column(String, nullable=False, index=True)  # Reference to expenses
    user_id = Column(String, nullable=False, index=True)  # Reference to user service
    share_amount = Column(DECIMAL(10, 2), nullable=False)
    is_settled = Column(Boolean, nullable=False, default=False)
