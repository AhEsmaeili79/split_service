from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException
from typing import List, Optional, Dict
from decimal import Decimal
from app.models.groups import Expense, ExpenseShare, Settlement, GroupMember
from app.schemas.expense_schema import (
    ExpenseCreate, ExpenseUpdate, ExpenseOut, ExpenseShareCreate,
    ExpenseShareOut, SettlementCreate, SettlementOut, DebtSummary, OptimizedSettlement
)


def create_expense(db: Session, group_id: str, expense_data: ExpenseCreate, paid_by: str, shares_data: List[ExpenseShareCreate]) -> Expense:
    """Create a new expense with shares"""
    from .group_service import is_group_member, get_group_members

    # Validate that payer is a group member
    if not is_group_member(db, group_id, paid_by):
        raise HTTPException(status_code=403, detail="Only group members can create expenses")

    # Validate total shares equal expense amount
    total_shares = sum(share.share_amount for share in shares_data)
    if total_shares != expense_data.amount:
        raise HTTPException(status_code=400, detail="Total shares must equal expense amount")

    # Validate all share recipients are group members
    group_members = {member.user_id for member in get_group_members(db, group_id)}
    for share in shares_data:
        if share.user_id not in group_members:
            raise HTTPException(status_code=400, detail=f"User {share.user_id} is not a member of this group")

    # Create expense
    expense = Expense(
        group_id=group_id,
        group_category_id=expense_data.group_category_id,
        title=expense_data.title,
        amount=expense_data.amount,
        paid_by=paid_by,
        description=expense_data.description,
        receipt_url=expense_data.receipt_url,
        date=expense_data.date
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    # Create expense shares
    for share_data in shares_data:
        share = ExpenseShare(
            expense_id=expense.id,
            user_id=share_data.user_id,
            share_amount=share_data.share_amount
        )
        db.add(share)

    db.commit()
    return expense


def get_expense(db: Session, expense_id: str) -> Optional[Expense]:
    """Get an expense by ID"""
    return db.query(Expense).filter(Expense.id == expense_id).first()


def get_group_expenses(db: Session, group_id: str) -> List[Expense]:
    """Get all expenses for a group"""
    return db.query(Expense).filter(Expense.group_id == group_id).all()


def get_category_expenses(db: Session, category_id: str) -> List[Expense]:
    """Get all expenses for a category"""
    return db.query(Expense).filter(Expense.group_category_id == category_id).all()


def update_expense(db: Session, expense_id: str, update_data: ExpenseUpdate, user_id: str) -> Expense:
    """Update an expense (owner or admin only)"""
    from .group_service import is_group_admin

    expense = get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Check permissions
    is_admin = is_group_admin(db, expense.group_id, user_id)
    if expense.paid_by != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Only expense creator or group admin can update expense")

    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(expense, field, value)

    db.commit()
    db.refresh(expense)
    return expense


def delete_expense(db: Session, expense_id: str, user_id: str):
    """Delete an expense (owner or admin only)"""
    from .group_service import is_group_admin

    expense = get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Check permissions
    is_admin = is_group_admin(db, expense.group_id, user_id)
    if expense.paid_by != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Only expense creator or group admin can delete expense")

    db.delete(expense)
    db.commit()


def get_expense_shares(db: Session, expense_id: str) -> List[ExpenseShare]:
    """Get all shares for an expense"""
    return db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()


def settle_expense_share(db: Session, share_id: str, user_id: str):
    """Mark an expense share as settled"""
    share = db.query(ExpenseShare).filter(ExpenseShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Expense share not found")

    # Only the person who owes can settle their own share
    if share.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only settle your own shares")

    share.is_settled = True
    db.commit()
    db.refresh(share)
    return share


def create_settlement(db: Session, group_id: str, settlement_data: SettlementCreate, user_id: str) -> Settlement:
    """Create a manual settlement"""
    from .group_service import is_group_member

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


def get_debt_summary(db: Session, group_id: str) -> List[DebtSummary]:
    """Calculate debt summary for all group members"""
    from .group_service import get_group_members

    members = get_group_members(db, group_id)
    summary = []

    for member in members:
        user_id = member.user_id

        # Calculate total owed (what others owe this user)
        total_owed = db.query(func.sum(ExpenseShare.share_amount)).join(Expense).filter(
            and_(
                Expense.group_id == group_id,
                Expense.paid_by == user_id,
                ExpenseShare.expense_id == Expense.id,
                ExpenseShare.is_settled == False
            )
        ).scalar() or Decimal('0')

        # Calculate total owes (what this user owes to others)
        total_owes = db.query(func.sum(ExpenseShare.share_amount)).join(Expense).filter(
            and_(
                Expense.group_id == group_id,
                Expense.paid_by != user_id,
                ExpenseShare.user_id == user_id,
                ExpenseShare.expense_id == Expense.id,
                ExpenseShare.is_settled == False
            )
        ).scalar() or Decimal('0')

        # Subtract settlements
        settlements_received = db.query(func.sum(Settlement.amount)).filter(
            and_(Settlement.group_id == group_id, Settlement.to_user_id == user_id)
        ).scalar() or Decimal('0')

        settlements_paid = db.query(func.sum(Settlement.amount)).filter(
            and_(Settlement.group_id == group_id, Settlement.from_user_id == user_id)
        ).scalar() or Decimal('0')

        net_balance = (total_owed - settlements_received) - (total_owes - settlements_paid)

        summary.append(DebtSummary(
            user_id=user_id,
            total_owed=total_owed,
            total_owes=total_owes,
            net_balance=net_balance
        ))

    return summary


def optimize_settlements(debt_summary: List[DebtSummary]) -> List[OptimizedSettlement]:
    """Optimize settlements using debt simplification algorithm"""
    # Create balance map
    balances = {debt.user_id: debt.net_balance for debt in debt_summary}

    creditors = [(uid, bal) for uid, bal in balances.items() if bal > 0]
    debtors = [(uid, -bal) for uid, bal in balances.items() if bal < 0]

    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    settlements = []
    i, j = 0, 0

    while i < len(creditors) and j < len(debtors):
        creditor_id, credit_amount = creditors[i]
        debtor_id, debt_amount = debtors[j]

        settlement_amount = min(credit_amount, debt_amount)

        if settlement_amount > 0:
            settlements.append(OptimizedSettlement(
                from_user_id=debtor_id,
                to_user_id=creditor_id,
                amount=settlement_amount
            ))

        creditors[i] = (creditor_id, credit_amount - settlement_amount)
        debtors[j] = (debtor_id, debt_amount - settlement_amount)

        if creditors[i][1] == 0:
            i += 1
        if debtors[j][1] == 0:
            j += 1

    return settlements
