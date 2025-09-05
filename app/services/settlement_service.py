from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException
from typing import List
from app.models.settlements import Settlement
from app.schemas.settlement_schema import SettlementCreate, SettlementOut, OptimizedSettlement


def create_settlement(db: Session, group_id: str, settlement_data: SettlementCreate, user_id: str) -> Settlement:
    """Create a manual settlement"""
    from app.services.group_service import is_group_member

    # Validate both users are group members
    if not is_group_member(db, group_id, settlement_data.from_user_id):
        raise HTTPException(status_code=400, detail="From user is not a member of this group")

    if not is_group_member(db, group_id, settlement_data.to_user_id):
        raise HTTPException(status_code=400, detail="To user is not a member of this group")

    # Users can only create settlements they're involved in
    if user_id not in [settlement_data.from_user_id, settlement_data.to_user_id]:
        raise HTTPException(status_code=403, detail="You can only create settlements you're involved in")

    settlement = Settlement(
        group_id=group_id,
        from_user_id=settlement_data.from_user_id,
        to_user_id=settlement_data.to_user_id,
        amount=settlement_data.amount
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)
    return settlement


def get_group_settlements(db: Session, group_id: str) -> List[Settlement]:
    """Get all settlements for a group"""
    return db.query(Settlement).filter(Settlement.group_id == group_id).all()


def get_settlement(db: Session, settlement_id: str) -> Settlement:
    """Get a settlement by ID"""
    return db.query(Settlement).filter(Settlement.id == settlement_id).first()
