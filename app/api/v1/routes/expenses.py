from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.services.auth.jwt_handler import get_current_user
from app.services.expense_service import (
    create_expense, get_expense, get_group_expenses, get_category_expenses,
    update_expense, delete_expense, get_expense_shares, settle_expense_share
)
from app.services.group_service import get_group_by_slug
from app.schemas.expense_schema import (
    ExpenseCreate, ExpenseUpdate, ExpenseOut, ExpenseWithShares,
    ExpenseShareCreate, ExpenseShareOut
)

router = APIRouter(prefix="/expenses", tags=["expenses"])

def get_current_user_id(access_token: str = Header(..., description="Access token (without Bearer)")):
    """Extract current user ID from JWT token"""
    if access_token.startswith("Bearer "):
        access_token = access_token.replace("Bearer ", "")
    user_id = get_current_user(access_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.post("/groups/{group_slug}", response_model=ExpenseOut)
def create_new_expense(
    group_slug: str,
    expense_data: ExpenseCreate,
    shares_data: List[ExpenseShareCreate],
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new expense with shares"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return create_expense(db, group.id, expense_data, user_id, shares_data)


@router.get("/groups/{group_slug}", response_model=List[ExpenseWithShares])
def get_group_expenses_list(
    group_slug: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get all expenses for a group"""
    group = get_group_by_slug(db, group_slug)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    from app.services.group_service import is_group_member
    if not is_group_member(db, group.id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    expenses = get_group_expenses(db, group.id)
    result = []

    for expense in expenses:
        shares = get_expense_shares(db, expense.id)
        result.append(ExpenseWithShares(
            id=expense.id,
            group_id=expense.group_id,
            group_category_id=expense.group_category_id,
            title=expense.title,
            amount=expense.amount,
            paid_by=expense.paid_by,
            description=expense.description,
            receipt_url=expense.receipt_url,
            date=expense.date,
            created_at=expense.created_at,
            shares=[ExpenseShareOut(
                id=share.id,
                expense_id=share.expense_id,
                user_id=share.user_id,
                share_amount=share.share_amount,
                is_settled=share.is_settled
            ) for share in shares]
        ))

    return result


@router.get("/categories/{category_id}", response_model=List[ExpenseOut])
def get_category_expenses_list(
    category_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get all expenses for a category"""
    # Check if user has access to this category's group
    from app.models.groups import GroupCategory
    category = db.query(GroupCategory).filter(GroupCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    from app.services.group_service import is_group_member
    if not is_group_member(db, category.group_id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    return get_category_expenses(db, category_id)


@router.get("/{expense_id}", response_model=ExpenseWithShares)
def get_expense_details(
    expense_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get expense details with shares"""
    expense = get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    from app.services.group_service import is_group_member
    if not is_group_member(db, expense.group_id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this group")

    shares = get_expense_shares(db, expense_id)
    return ExpenseWithShares(
        id=expense.id,
        group_id=expense.group_id,
        group_category_id=expense.group_category_id,
        title=expense.title,
        amount=expense.amount,
        paid_by=expense.paid_by,
        description=expense.description,
        receipt_url=expense.receipt_url,
        date=expense.date,
        created_at=expense.created_at,
        shares=[ExpenseShareOut(
            id=share.id,
            expense_id=share.expense_id,
            user_id=share.user_id,
            share_amount=share.share_amount,
            is_settled=share.is_settled
        ) for share in shares]
    )


@router.patch("/{expense_id}", response_model=ExpenseOut)
def update_existing_expense(
    expense_id: str,
    update_data: ExpenseUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update an expense (owner or admin only)"""
    return update_expense(db, expense_id, update_data, user_id)


@router.delete("/{expense_id}")
def delete_existing_expense(
    expense_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete an expense (owner or admin only)"""
    delete_expense(db, expense_id, user_id)
    return {"message": "Expense deleted successfully"}


@router.patch("/shares/{share_id}/settle")
def settle_expense_share_endpoint(
    share_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Mark an expense share as settled"""
    settle_expense_share(db, share_id, user_id)
    return {"message": "Share settled successfully"}


