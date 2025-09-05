import enum
import uuid
from sqlalchemy.sql import func
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Boolean, DECIMAL, Text
from app.db.database import Base


class RoundingOption(str, enum.Enum):
    up = "up"
    down = "down"
    none = "none"


class Group(Base):
    __tablename__ = "groups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    name = Column(String(100), nullable=False, index=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)  # URL-friendly identifier
    image_url = Column(String, nullable=True)
    created_by = Column(String, nullable=False)  # Reference to user service (no FK constraint)
    rounding_option = Column(Enum(RoundingOption), nullable=False, default=RoundingOption.none)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)  # Reference to user service
    is_admin = Column(Boolean, nullable=False, default=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GroupCategory(Base):
    __tablename__ = "group_categories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    group_category_id = Column(String, ForeignKey("group_categories.id"), nullable=False)
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
    expense_id = Column(String, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)  # Reference to user service
    share_amount = Column(DECIMAL(10, 2), nullable=False)
    is_settled = Column(Boolean, nullable=False, default=False)


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    group_id = Column(String, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    from_user_id = Column(String, nullable=False, index=True)  # Reference to user service
    to_user_id = Column(String, nullable=False, index=True)  # Reference to user service
    amount = Column(DECIMAL(10, 2), nullable=False)
    settled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
