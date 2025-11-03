"""
Pytest configuration and fixtures for split_service tests.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from typing import Dict, List
from unittest.mock import Mock, MagicMock

from app.utils.min_cash_flow import calculate_balances, min_cash_flow
from app.schemas.expense_schema import DebtSummary
from app.schemas.settlement_schema import OptimizedSettlement


@pytest.fixture
def sample_expenses():
    """Sample expenses for testing."""
    return [
        {"payer": "A", "amount": Decimal("120"), "participants": ["A", "B", "C"]},
        {"payer": "B", "amount": Decimal("60"), "participants": ["B", "C"]},
        {"payer": "C", "amount": Decimal("40"), "participants": ["A", "C", "D"]},
    ]


@pytest.fixture
def sample_balances():
    """Sample balances for testing."""
    return {
        "A": Decimal("66.67"),
        "B": Decimal("-10.00"),
        "C": Decimal("-43.33"),
        "D": Decimal("-13.33")
    }


@pytest.fixture
def sample_debt_summary():
    """Sample debt summary for testing."""
    return [
        DebtSummary(
            user_id="A",
            total_owed=Decimal("120"),
            total_owes=Decimal("53.33"),
            net_balance=Decimal("66.67")
        ),
        DebtSummary(
            user_id="B",
            total_owed=Decimal("60"),
            total_owes=Decimal("70"),
            net_balance=Decimal("-10")
        ),
        DebtSummary(
            user_id="C",
            total_owed=Decimal("40"),
            total_owes=Decimal("83.33"),
            net_balance=Decimal("-43.33")
        ),
        DebtSummary(
            user_id="D",
            total_owed=Decimal("0"),
            total_owes=Decimal("13.33"),
            net_balance=Decimal("-13.33")
        ),
    ]


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.query = Mock()
    session.delete = Mock()
    return session


def verify_settlements_settle_debts(balances: Dict[str, Decimal], settlements: List[Dict]) -> None:
    """
    Helper to verify settlements settle all debts.
    
    Settlement logic:
    - If user receives money (positive settlement_total), it reduces what they're owed
    - If user pays money (negative settlement_total), it reduces what they owe
    - Final balance = initial_balance - settlement_total
    """
    settlement_totals = {}
    
    for settlement in settlements:
        from_user = settlement["from"]
        to_user = settlement["to"]
        amount = settlement["amount"]
        
        if from_user not in settlement_totals:
            settlement_totals[from_user] = Decimal("0")
        if to_user not in settlement_totals:
            settlement_totals[to_user] = Decimal("0")
        
        settlement_totals[from_user] -= amount
        settlement_totals[to_user] += amount
    
    for user, initial_balance in balances.items():
        if abs(initial_balance) <= Decimal("0.01"):
            continue
        
        settlement_total = settlement_totals.get(user, Decimal("0"))
        final_balance = initial_balance - settlement_total
        
        assert abs(final_balance) <= Decimal("0.01"), \
            f"User {user} not settled: initial={initial_balance}, " \
            f"settlement_total={settlement_total}, final={final_balance}"

