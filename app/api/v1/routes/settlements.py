from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.services.auth.jwt_handler import get_current_user
from app.services.settlement_service import create_settlement, get_group_settlements
from app.services.expense_service import get_debt_summary, optimize_settlements
from app.services.group_service import get_group_by_slug
from app.schemas.settlement_schema import SettlementCreate, SettlementOut, OptimizedSettlement
from app.schemas.expense_schema import DebtSummary

router = APIRouter(prefix="/settlements", tags=["settlements"])

def get_current_user_id(access_token: str = Header(..., description="Access token (without Bearer)")):
    """Extract current user ID from JWT token"""
    if access_token.startswith("Bearer "):
        access_token = access_token.replace("Bearer ", "")
    user_id = get_current_user(access_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/groups/{group_slug}", response_model=SettlementOut)
def create_new_settlement(
    group_slug: str,
    settlement_data: SettlementCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a manual settlement"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return create_settlement(db, group.id, settlement_data, user_id)


@router.get("/groups/{group_slug}", response_model=List[SettlementOut])
def get_group_settlements_list(
    group_slug: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get all settlements for a group"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    from app.services.group_service import is_group_member
    if not is_group_member(db, group.id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    return get_group_settlements(db, group.id)


@router.get("/groups/{group_slug}/debts", response_model=List[DebtSummary])
def get_group_debt_summary(
    group_slug: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get debt summary for all group members"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    from app.services.group_service import is_group_member
    if not is_group_member(db, group.id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    return get_debt_summary(db, group.id)


@router.get("/groups/{group_slug}/optimize", response_model=List[OptimizedSettlement])
def get_optimized_settlements(
    group_slug: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get optimized settlement suggestions"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    from app.services.group_service import is_group_member
    if not is_group_member(db, group.id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    debt_summary = get_debt_summary(db, group.id)
    return optimize_settlements(debt_summary)
