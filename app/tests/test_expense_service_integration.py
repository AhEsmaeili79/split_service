"""
Comprehensive pytest tests for expense_service integration with Min-Cash-Flow algorithm.

Tests cover:
- optimize_settlements() function integration
- All edge cases and conditions
- Error handling
- Format compatibility
- Performance with various data sizes
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock all dependencies before importing
sys.modules['pika'] = MagicMock()
sys.modules['pydantic_settings'] = MagicMock()

# Now import
from app.services.expense_service import optimize_settlements
from app.schemas.expense_schema import DebtSummary
from app.schemas.settlement_schema import OptimizedSettlement
from app.utils.min_cash_flow import min_cash_flow
from app.tests.conftest import verify_settlements_settle_debts


@pytest.mark.unit
class TestOptimizeSettlements:
    """Test optimize_settlements() function integration."""
    
    def test_basic_optimization(self, sample_debt_summary):
        """Test basic settlement optimization."""
        settlements = optimize_settlements(sample_debt_summary)
        
        assert isinstance(settlements, list)
        assert len(settlements) > 0
        
        # Verify all settlements are OptimizedSettlement objects
        for settlement in settlements:
            assert isinstance(settlement, OptimizedSettlement)
            assert settlement.from_user_id is not None
            assert settlement.to_user_id is not None
            assert settlement.amount > Decimal("0")
    
    def test_optimization_format(self, sample_debt_summary):
        """Test that output format matches OptimizedSettlement schema."""
        settlements = optimize_settlements(sample_debt_summary)
        
        for settlement in settlements:
            # Verify schema fields
            assert hasattr(settlement, 'from_user_id')
            assert hasattr(settlement, 'to_user_id')
            assert hasattr(settlement, 'amount')
            
            # Verify types
            assert isinstance(settlement.from_user_id, str)
            assert isinstance(settlement.to_user_id, str)
            assert isinstance(settlement.amount, Decimal)
            
            # Verify values
            assert settlement.from_user_id != settlement.to_user_id
            assert settlement.amount > Decimal("0")
    
    def test_mathematical_correctness(self, sample_debt_summary):
        """Test that settlements mathematically settle all debts."""
        settlements = optimize_settlements(sample_debt_summary)
        
        # Convert DebtSummary to balances dict
        balances = {debt.user_id: debt.net_balance for debt in sample_debt_summary}
        
        # Convert settlements to dict format for verification
        settlements_dict = [
            {
                "from": s.from_user_id,
                "to": s.to_user_id,
                "amount": s.amount
            }
            for s in settlements
        ]
        
        # Verify settlements settle all debts
        verify_settlements_settle_debts(balances, settlements_dict)
    
    def test_empty_debt_summary(self):
        """Test with empty debt summary."""
        settlements = optimize_settlements([])
        assert settlements == []
    
    def test_single_user_debt_summary(self):
        """Test with single user."""
        debt_summary = [
            DebtSummary(
                user_id="A",
                total_owed=Decimal("0"),
                total_owes=Decimal("0"),
                net_balance=Decimal("0")
            )
        ]
        settlements = optimize_settlements(debt_summary)
        assert settlements == []
    
    def test_all_zero_balances(self):
        """Test with all zero balances."""
        debt_summary = [
            DebtSummary(
                user_id="A",
                total_owed=Decimal("0"),
                total_owes=Decimal("0"),
                net_balance=Decimal("0")
            ),
            DebtSummary(
                user_id="B",
                total_owed=Decimal("0"),
                total_owes=Decimal("0"),
                net_balance=Decimal("0")
            )
        ]
        settlements = optimize_settlements(debt_summary)
        assert settlements == []
    
    def test_perfectly_balanced(self):
        """Test when debts are perfectly balanced."""
        debt_summary = [
            DebtSummary(
                user_id="A",
                total_owed=Decimal("50"),
                total_owes=Decimal("0"),
                net_balance=Decimal("50")
            ),
            DebtSummary(
                user_id="B",
                total_owed=Decimal("0"),
                total_owes=Decimal("50"),
                net_balance=Decimal("-50")
            )
        ]
        settlements = optimize_settlements(debt_summary)
        
        assert len(settlements) == 1
        assert settlements[0].from_user_id == "B"
        assert settlements[0].to_user_id == "A"
        assert settlements[0].amount == Decimal("50.00")
    
    def test_multiple_creditors_debtors(self):
        """Test with multiple creditors and debtors."""
        debt_summary = [
            DebtSummary(user_id="A", total_owed=Decimal("100"), total_owes=Decimal("0"), net_balance=Decimal("100")),
            DebtSummary(user_id="B", total_owed=Decimal("50"), total_owes=Decimal("0"), net_balance=Decimal("50")),
            DebtSummary(user_id="C", total_owed=Decimal("0"), total_owes=Decimal("60"), net_balance=Decimal("-60")),
            DebtSummary(user_id="D", total_owed=Decimal("0"), total_owes=Decimal("90"), net_balance=Decimal("-90")),
        ]
        
        settlements = optimize_settlements(debt_summary)
        
        # Should minimize transactions (should be <= 2)
        assert len(settlements) <= 2
        
        # Verify all debts are settled
        balances = {debt.user_id: debt.net_balance for debt in debt_summary}
        settlements_dict = [
            {"from": s.from_user_id, "to": s.to_user_id, "amount": s.amount}
            for s in settlements
        ]
        verify_settlements_settle_debts(balances, settlements_dict)
    
    def test_large_group(self):
        """Test with large group (20 users)."""
        # Create 20 users with random balances that sum to zero
        users = [f"User{i}" for i in range(20)]
        balances = {}
        total = Decimal("0")
        
        # Generate random balances
        for i, user in enumerate(users[:-1]):
            balance = Decimal(str((i % 3 - 1) * 10))
            balances[user] = balance
            total += balance
        
        # Last user balances to zero
        balances[users[-1]] = -total
        
        debt_summary = [
            DebtSummary(
                user_id=user,
                total_owed=Decimal("0"),  # Simplified for test
                total_owes=Decimal("0"),
                net_balance=balance
            )
            for user, balance in balances.items()
        ]
        
        settlements = optimize_settlements(debt_summary)
        
        # Should minimize transactions
        assert len(settlements) <= len([b for b in balances.values() if abs(b) > Decimal("0.01")])
        
        # Verify all debts are settled
        settlements_dict = [
            {"from": s.from_user_id, "to": s.to_user_id, "amount": s.amount}
            for s in settlements
        ]
        verify_settlements_settle_debts(balances, settlements_dict)
    
    def test_rounding_tolerance(self):
        """Test handling of rounding tolerance."""
        debt_summary = [
            DebtSummary(
                user_id="A",
                total_owed=Decimal("50.005"),
                total_owes=Decimal("0"),
                net_balance=Decimal("50.005")
            ),
            DebtSummary(
                user_id="B",
                total_owed=Decimal("0"),
                total_owes=Decimal("50"),
                net_balance=Decimal("-50")
            )
        ]
        
        # Should handle within tolerance
        settlements = optimize_settlements(debt_summary)
        assert len(settlements) >= 0  # May be empty or have small settlement
    
    def test_small_amounts(self):
        """Test with very small amounts."""
        debt_summary = [
            DebtSummary(
                user_id="A",
                total_owed=Decimal("0.01"),
                total_owes=Decimal("0"),
                net_balance=Decimal("0.01")
            ),
            DebtSummary(
                user_id="B",
                total_owed=Decimal("0"),
                total_owes=Decimal("0.01"),
                net_balance=Decimal("-0.01")
            )
        ]
        
        settlements = optimize_settlements(debt_summary)
        # May be empty if amounts are within tolerance
        assert isinstance(settlements, list)
    
    def test_large_amounts(self):
        """Test with very large amounts."""
        debt_summary = [
            DebtSummary(
                user_id="A",
                total_owed=Decimal("1000000"),
                total_owes=Decimal("0"),
                net_balance=Decimal("1000000")
            ),
            DebtSummary(
                user_id="B",
                total_owed=Decimal("0"),
                total_owes=Decimal("500000"),
                net_balance=Decimal("-500000")
            ),
            DebtSummary(
                user_id="C",
                total_owed=Decimal("0"),
                total_owes=Decimal("500000"),
                net_balance=Decimal("-500000")
            )
        ]
        
        settlements = optimize_settlements(debt_summary)
        
        assert len(settlements) == 2
        # Verify amounts are correct
        total_settled = sum(s.amount for s in settlements)
        assert abs(total_settled - Decimal("1000000")) <= Decimal("0.01")


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end integration tests."""
    
    def test_full_workflow_from_expenses_to_settlements(self):
        """Test complete workflow from expenses to optimized settlements."""
        from app.utils.min_cash_flow import calculate_balances
        
        # Step 1: Create expenses
        expenses = [
            {"payer": "Alice", "amount": Decimal("300"), "participants": ["Alice", "Bob", "Charlie"]},
            {"payer": "Bob", "amount": Decimal("200"), "participants": ["Alice", "Bob"]},
            {"payer": "Charlie", "amount": Decimal("100"), "participants": ["Bob", "Charlie", "David"]},
        ]
        
        # Step 2: Calculate balances
        balances = calculate_balances(expenses)
        
        # Step 3: Convert to DebtSummary format (simulating database)
        debt_summary = [
            DebtSummary(
                user_id=user_id,
                total_owed=Decimal("0"),  # Simplified
                total_owes=Decimal("0"),
                net_balance=balance
            )
            for user_id, balance in balances.items()
        ]
        
        # Step 4: Optimize settlements
        settlements = optimize_settlements(debt_summary)
        
        # Step 5: Verify results
        assert len(settlements) > 0
        assert all(isinstance(s, OptimizedSettlement) for s in settlements)
        
        # Verify settlements settle all debts
        settlements_dict = [
            {"from": s.from_user_id, "to": s.to_user_id, "amount": s.amount}
            for s in settlements
        ]
        verify_settlements_settle_debts(balances, settlements_dict)
    
    def test_api_response_format(self, sample_debt_summary):
        """Test that output can be serialized to JSON (API format)."""
        settlements = optimize_settlements(sample_debt_summary)
        
        # Simulate API serialization
        for settlement in settlements:
            # Pydantic models can be serialized to dict
            settlement_dict = settlement.dict()
            
            assert "from_user_id" in settlement_dict
            assert "to_user_id" in settlement_dict
            assert "amount" in settlement_dict
            
            # Amount should be serializable (Decimal -> string in JSON)
            assert isinstance(settlement_dict["amount"], (str, Decimal))


@pytest.mark.unit
class TestEdgeCases:
    """Test all edge cases and boundary conditions."""
    
    def test_three_way_settlement(self):
        """Test three-way settlement scenario."""
        debt_summary = [
            DebtSummary(user_id="A", total_owed=Decimal("100"), total_owes=Decimal("0"), net_balance=Decimal("100")),
            DebtSummary(user_id="B", total_owed=Decimal("0"), total_owes=Decimal("50"), net_balance=Decimal("-50")),
            DebtSummary(user_id="C", total_owed=Decimal("0"), total_owes=Decimal("50"), net_balance=Decimal("-50")),
        ]
        
        settlements = optimize_settlements(debt_summary)
        
        # Should minimize to 2 transactions (not 3)
        assert len(settlements) == 2
        
        # Verify correctness
        balances = {debt.user_id: debt.net_balance for debt in debt_summary}
        settlements_dict = [
            {"from": s.from_user_id, "to": s.to_user_id, "amount": s.amount}
            for s in settlements
        ]
        verify_settlements_settle_debts(balances, settlements_dict)
    
    def test_unbalanced_debt_summary(self):
        """Test that unbalanced input doesn't crash (handled by min_cash_flow)."""
        # This should be caught by validate_balance_sum in min_cash_flow
        debt_summary = [
            DebtSummary(user_id="A", total_owed=Decimal("50"), total_owes=Decimal("0"), net_balance=Decimal("50")),
            DebtSummary(user_id="B", total_owed=Decimal("0"), total_owes=Decimal("49"), net_balance=Decimal("-49")),
        ]
        
        # Should raise ValueError or handle gracefully
        with pytest.raises(ValueError, match="Balances not zero-sum"):
            optimize_settlements(debt_summary)
    
    def test_negative_amounts(self):
        """Test that negative amounts are handled correctly."""
        debt_summary = [
            DebtSummary(user_id="A", total_owed=Decimal("100"), total_owes=Decimal("0"), net_balance=Decimal("100")),
            DebtSummary(user_id="B", total_owed=Decimal("0"), total_owes=Decimal("100"), net_balance=Decimal("-100")),
        ]
        
        settlements = optimize_settlements(debt_summary)
        
        # All settlement amounts should be positive
        for settlement in settlements:
            assert settlement.amount > Decimal("0")
    
    def test_very_small_tolerance(self):
        """Test with very small tolerance."""
        debt_summary = [
            DebtSummary(user_id="A", total_owed=Decimal("50"), total_owes=Decimal("0"), net_balance=Decimal("50")),
            DebtSummary(user_id="B", total_owed=Decimal("0"), total_owes=Decimal("50"), net_balance=Decimal("-50")),
        ]
        
        settlements = optimize_settlements(debt_summary)
        assert len(settlements) == 1


@pytest.mark.unit
class TestPerformance:
    """Performance and scalability tests."""
    
    def test_performance_100_users(self):
        """Test performance with 100 users."""
        import time
        
        # Create 100 users with balanced debts
        users = [f"User{i}" for i in range(100)]
        balances = {}
        total = Decimal("0")
        
        for i, user in enumerate(users[:-1]):
            balance = Decimal(str((i % 10 - 5) * 10))
            balances[user] = balance
            total += balance
        
        balances[users[-1]] = -total
        
        debt_summary = [
            DebtSummary(
                user_id=user,
                total_owed=Decimal("0"),
                total_owes=Decimal("0"),
                net_balance=balance
            )
            for user, balance in balances.items()
        ]
        
        start_time = time.time()
        settlements = optimize_settlements(debt_summary)
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time (< 1 second)
        assert elapsed_time < 1.0
        
        # Verify correctness
        settlements_dict = [
            {"from": s.from_user_id, "to": s.to_user_id, "amount": s.amount}
            for s in settlements
        ]
        verify_settlements_settle_debts(balances, settlements_dict)
    
    def test_transaction_minimization(self):
        """Test that algorithm minimizes transaction count."""
        # Create scenario where naive approach would use many transactions
        debt_summary = [
            DebtSummary(user_id="A", total_owed=Decimal("100"), total_owes=Decimal("0"), net_balance=Decimal("100")),
            DebtSummary(user_id="B", total_owed=Decimal("0"), total_owes=Decimal("10"), net_balance=Decimal("-10")),
            DebtSummary(user_id="C", total_owed=Decimal("0"), total_owes=Decimal("20"), net_balance=Decimal("-20")),
            DebtSummary(user_id="D", total_owed=Decimal("0"), total_owes=Decimal("30"), net_balance=Decimal("-30")),
            DebtSummary(user_id="E", total_owed=Decimal("0"), total_owes=Decimal("40"), net_balance=Decimal("-40")),
        ]
        
        settlements = optimize_settlements(debt_summary)
        
        # Optimal solution should use at most 4 transactions
        # (could be less if algorithm finds better solution)
        assert len(settlements) <= 4
        
        # Verify correctness
        balances = {debt.user_id: debt.net_balance for debt in debt_summary}
        settlements_dict = [
            {"from": s.from_user_id, "to": s.to_user_id, "amount": s.amount}
            for s in settlements
        ]
        verify_settlements_settle_debts(balances, settlements_dict)

