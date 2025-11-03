"""
Standalone test for optimize_settlements function.

This test directly tests the optimize_settlements logic without requiring
full service dependencies.
"""
import pytest
from decimal import Decimal
from app.schemas.expense_schema import DebtSummary
from app.schemas.settlement_schema import OptimizedSettlement
from app.utils.min_cash_flow import min_cash_flow


def test_optimize_settlements_direct():
    """Test optimize_settlements logic directly."""
    # Simulate what optimize_settlements does
    debt_summary = [
        DebtSummary(user_id="A", total_owed=Decimal("66.67"), total_owes=Decimal("0"), net_balance=Decimal("66.67")),
        DebtSummary(user_id="B", total_owed=Decimal("60"), total_owes=Decimal("70"), net_balance=Decimal("-10")),
        DebtSummary(user_id="C", total_owed=Decimal("40"), total_owes=Decimal("83.33"), net_balance=Decimal("-43.33")),
        DebtSummary(user_id="D", total_owed=Decimal("0"), total_owes=Decimal("13.33"), net_balance=Decimal("-13.33")),
    ]
    
    # Create balance map (what optimize_settlements does)
    balances = {debt.user_id: debt.net_balance for debt in debt_summary}
    
    # Filter zero balances
    active_balances = {
        user_id: balance
        for user_id, balance in balances.items()
        if abs(balance) > Decimal('0.01')
    }
    
    # Apply Min-Cash-Flow algorithm
    settlements_dict = min_cash_flow(active_balances)
    
    # Convert to OptimizedSettlement format
    settlements = [
        OptimizedSettlement(
            from_user_id=s['from'],
            to_user_id=s['to'],
            amount=s['amount']
        )
        for s in settlements_dict
    ]
    
    # Verify results
    assert len(settlements) == 3
    assert all(isinstance(s, OptimizedSettlement) for s in settlements)
    
    # Verify format
    for s in settlements:
        assert isinstance(s.from_user_id, str)
        assert isinstance(s.to_user_id, str)
        assert isinstance(s.amount, Decimal)
        assert s.amount > Decimal("0")
    
    # Verify mathematical correctness
    settlement_totals = {}
    for s in settlements:
        from_user = s.from_user_id
        to_user = s.to_user_id
        amount = s.amount
        settlement_totals[from_user] = settlement_totals.get(from_user, Decimal("0")) - amount
        settlement_totals[to_user] = settlement_totals.get(to_user, Decimal("0")) + amount
    
    for user, initial_balance in active_balances.items():
        final_balance = initial_balance - settlement_totals.get(user, Decimal("0"))
        assert abs(final_balance) <= Decimal("0.01"), \
            f"User {user} not settled: initial={initial_balance}, final={final_balance}"


if __name__ == "__main__":
    test_optimize_settlements_direct()
    print("✓ optimize_settlements logic test passed!")

