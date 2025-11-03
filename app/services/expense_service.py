from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException
from typing import List, Optional, Dict
from decimal import Decimal
from app.models.expenses import Expense, ExpenseShare
from app.models.groups import GroupMember
from app.schemas.expense_schema import (
    ExpenseCreate, ExpenseUpdate, ExpenseOut, ExpenseShareCreate,
    ExpenseShareOut, DebtSummary
)
from app.schemas.settlement_schema import OptimizedSettlement


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




def get_debt_summary(db: Session, group_id: str) -> List[DebtSummary]:
    """Calculate debt summary for all group members"""
    from .group_service import get_group_members
    from app.models.settlements import Settlement

    members = get_group_members(db, group_id)
    summary = []

    for member in members:
        user_id = member.user_id

        # Calculate total owed (what others owe this user)
        total_owed = db.query(func.sum(ExpenseShare.share_amount))\
            .select_from(ExpenseShare)\
            .join(Expense, ExpenseShare.expense_id == Expense.id)\
            .filter(
                and_(
                    Expense.group_id == group_id,
                    Expense.paid_by == user_id,
                    ExpenseShare.is_settled == False
                )
            ).scalar() or Decimal('0')

        # Calculate total owes (what this user owes to others)
        total_owes = db.query(func.sum(ExpenseShare.share_amount))\
            .select_from(ExpenseShare)\
            .join(Expense, ExpenseShare.expense_id == Expense.id)\
            .filter(
                and_(
                    Expense.group_id == group_id,
                    Expense.paid_by != user_id,
                    ExpenseShare.user_id == user_id,
                    ExpenseShare.is_settled == False
                )
            ).scalar() or Decimal('0')

        # Subtract settlements
        settlements_received = db.query(func.sum(Settlement.amount))\
            .filter(
                and_(Settlement.group_id == group_id, Settlement.to_user_id == user_id)
            ).scalar() or Decimal('0')

        settlements_paid = db.query(func.sum(Settlement.amount))\
            .filter(
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
    """
    Optimize settlements using Min-Cash-Flow algorithm.
    
    This function uses a greedy algorithm to minimize the number of transactions
    needed to settle all debts within a group. It transforms the debt summary
    into a balance map and applies the Min-Cash-Flow algorithm.
    
    Args:
        debt_summary: List of DebtSummary objects containing user balances
    
    Returns:
        List of OptimizedSettlement objects representing minimal transactions
    
    Algorithm:
        - Converts DebtSummary list to balance dictionary
        - Applies Min-Cash-Flow greedy matching algorithm
        - Returns optimized settlement transactions
    """
    from app.utils.min_cash_flow import min_cash_flow
    
    # Create balance map from debt summary
    balances = {debt.user_id: debt.net_balance for debt in debt_summary}
    
    # Filter out zero balances (within tolerance)
    # The min_cash_flow function handles edge cases internally
    active_balances = {
        user_id: balance
        for user_id, balance in balances.items()
        if abs(balance) > Decimal('0.01')
    }
    
    # If no active balances, return empty list
    if not active_balances:
        return []
    
    # Apply Min-Cash-Flow algorithm
    # Returns list of dicts: [{"from": str, "to": str, "amount": Decimal}, ...]
    settlements_dict = min_cash_flow(active_balances)
    
    # Convert to OptimizedSettlement objects
    settlements = [
        OptimizedSettlement(
            from_user_id=settlement["from"],
            to_user_id=settlement["to"],
            amount=settlement["amount"]
        )
        for settlement in settlements_dict
    ]
    
    return settlements


def calculate_balances_from_expenses(db: Session, group_id: str) -> Dict[str, Decimal]:
    """
    Calculate balances directly from expenses (bypassing settlements).
    
    This is an alternative balance calculation that computes net balances
    directly from expense data, without considering existing settlements.
    Useful for testing, validation, and standalone calculations.
    
    Args:
        db: Database session
        group_id: Group ID to calculate balances for
    
    Returns:
        Dictionary mapping user_id -> net_balance (total_paid - total_share)
    
    Note:
        This function calculates balances from expenses only, ignoring
        any settlements that may have been recorded. Use get_debt_summary()
        if you need balances that account for settlements.
    """
    expenses = get_group_expenses(db, group_id)
    balances: Dict[str, Decimal] = {}
    
    for expense in expenses:
        payer_id = expense.paid_by
        expense_amount = expense.amount
        
        # Add to payer's balance (what they paid)
        if payer_id not in balances:
            balances[payer_id] = Decimal('0')
        balances[payer_id] += expense_amount
        
        # Get shares for this expense
        shares = get_expense_shares(db, expense.id)
        
        # Subtract each share from respective user's balance
        for share in shares:
            user_id = share.user_id
            share_amount = share.share_amount
            
            if user_id not in balances:
                balances[user_id] = Decimal('0')
            balances[user_id] -= share_amount
    
    # Round all balances using Decimal quantization
    from app.utils.min_cash_flow import round_decimal
    balances = {user_id: round_decimal(balance) for user_id, balance in balances.items()}
    
    return balances
