"""
Unit Tests for Min-Cash-Flow Algorithm

Tests cover:
- Equal split expenses
- Weighted split expenses
- Edge cases (zero balances, single user, large groups)
- Validation and error handling
- Rounding tolerance
"""

import pytest
from decimal import Decimal
from app.utils.min_cash_flow import (
    calculate_balances,
    min_cash_flow,
    min_cash_flow_detailed,
    round_decimal,
    validate_balance_sum
)


class TestRoundDecimal:
    """Test the round_decimal utility function."""
    
    def test_round_to_cents(self):
        """Test rounding to 0.01 precision."""
        assert round_decimal(Decimal("43.333333")) == Decimal("43.33")
        assert round_decimal(Decimal("43.336666")) == Decimal("43.34")
        # Note: 100.005 rounds to 100.00 with ROUND_HALF_EVEN (banker's rounding)
        assert round_decimal(Decimal("100.005")) == Decimal("100.00")
        assert round_decimal(Decimal("100.015")) == Decimal("100.02")  # This rounds up
    
    def test_custom_precision(self):
        """Test rounding with custom precision."""
        precision = Decimal("0.1")
        assert round_decimal(Decimal("43.34"), precision) == Decimal("43.3")
        assert round_decimal(Decimal("43.36"), precision) == Decimal("43.4")


class TestValidateBalanceSum:
    """Test the validate_balance_sum utility function."""
    
    def test_valid_balanced_sum(self):
        """Test validation passes for balanced sums."""
        balances = {"A": Decimal("50"), "B": Decimal("-50")}
        validate_balance_sum(balances)  # Should not raise
    
    def test_valid_within_tolerance(self):
        """Test validation passes when within tolerance."""
        balances = {"A": Decimal("50.005"), "B": Decimal("-50")}
        validate_balance_sum(balances, tolerance=Decimal("0.01"))
    
    def test_invalid_outside_tolerance(self):
        """Test validation fails when outside tolerance."""
        balances = {"A": Decimal("50"), "B": Decimal("-49")}
        with pytest.raises(ValueError, match="Balances not zero-sum"):
            validate_balance_sum(balances)


class TestCalculateBalances:
    """Test the calculate_balances function."""
    
    def test_equal_split(self):
        """Test equal split calculation."""
        expenses = [
            {"payer": "A", "amount": Decimal("120"), "participants": ["A", "B", "C"]},
        ]
        balances = calculate_balances(expenses)
        assert balances["A"] == Decimal("80.00")  # Paid 120, owes 40
        assert balances["B"] == Decimal("-40.00")  # Owed 40
        assert balances["C"] == Decimal("-40.00")  # Owed 40
    
    def test_weighted_split(self):
        """Test weighted split calculation."""
        expenses = [
            {
                "payer": "A",
                "amount": Decimal("100"),
                "participants": ["A", "B"],
                "weights": {"A": Decimal("0.6"), "B": Decimal("0.4")}
            }
        ]
        balances = calculate_balances(expenses)
        assert balances["A"] == Decimal("40.00")  # Paid 100, owes 60
        assert balances["B"] == Decimal("-40.00")  # Owed 40
    
    def test_weighted_split_invalid_sum(self):
        """Test that invalid weight sums raise ValueError."""
        expenses = [
            {
                "payer": "A",
                "amount": Decimal("100"),
                "participants": ["A", "B"],
                "weights": {"A": Decimal("0.6"), "B": Decimal("0.5")}  # Sums to 1.1
            }
        ]
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            calculate_balances(expenses)
    
    def test_multiple_expenses(self):
        """Test calculation with multiple expenses."""
        expenses = [
            {"payer": "A", "amount": Decimal("120"), "participants": ["A", "B", "C"]},
            {"payer": "B", "amount": Decimal("60"), "participants": ["B", "C"]},
            {"payer": "C", "amount": Decimal("40"), "participants": ["A", "C", "D"]},
        ]
        balances = calculate_balances(expenses)
        
        # Validate sum is zero
        total = sum(balances.values())
        assert abs(total) <= Decimal("0.01")
    
    def test_empty_expenses(self):
        """Test with empty expenses list."""
        balances = calculate_balances([])
        assert balances == {}


class TestMinCashFlow:
    """Test the min_cash_flow function."""
    
    def test_basic_settlement(self):
        """Test basic settlement calculation."""
        balances = {
            "A": Decimal("80"),
            "B": Decimal("-10"),
            "C": Decimal("-70")
        }
        settlements = min_cash_flow(balances)
        
        assert len(settlements) == 2
        # C should pay A $70
        # B should pay A $10
        settlement_dict = {(s["from"], s["to"]): s["amount"] for s in settlements}
        assert ("C", "A") in settlement_dict
        assert settlement_dict[("C", "A")] == Decimal("70.00")
        assert ("B", "A") in settlement_dict
        assert settlement_dict[("B", "A")] == Decimal("10.00")
    
    def test_example_from_spec(self):
        """Test with the exact example from the specification."""
        expenses = [
            {"payer": "A", "amount": Decimal("120"), "participants": ["A", "B", "C"]},
            {"payer": "B", "amount": Decimal("60"), "participants": ["B", "C"]},
            {"payer": "C", "amount": Decimal("40"), "participants": ["A", "C", "D"]},
        ]
        
        balances = calculate_balances(expenses)
        settlements = min_cash_flow(balances)
        
        # Verify all debts are settled
        # Sum up settlements to verify
        settlement_totals = {}
        for s in settlements:
            from_user = s["from"]
            to_user = s["to"]
            amount = s["amount"]
            
            if from_user not in settlement_totals:
                settlement_totals[from_user] = Decimal("0")
            if to_user not in settlement_totals:
                settlement_totals[to_user] = Decimal("0")
            
            settlement_totals[from_user] -= amount
            settlement_totals[to_user] += amount
        
        # Verify each user's final balance (original - settlements) is near zero
        for user, balance in balances.items():
            settlement_balance = settlement_totals.get(user, Decimal("0"))
            final_balance = balance - settlement_balance  # Settlement reduces balance
            assert abs(final_balance) <= Decimal("0.01"), \
                f"User {user} final balance {final_balance} not zero"
    
    def test_single_user(self):
        """Test edge case: single user."""
        balances = {"A": Decimal("0")}
        settlements = min_cash_flow(balances)
        assert settlements == []
    
    def test_all_zero_balances(self):
        """Test edge case: all zero balances."""
        balances = {"A": Decimal("0"), "B": Decimal("0"), "C": Decimal("0")}
        settlements = min_cash_flow(balances)
        assert settlements == []
    
    def test_perfectly_balanced(self):
        """Test when expenses are already perfectly balanced."""
        balances = {"A": Decimal("50"), "B": Decimal("-50")}
        settlements = min_cash_flow(balances)
        assert len(settlements) == 1
        assert settlements[0]["from"] == "B"
        assert settlements[0]["to"] == "A"
        assert settlements[0]["amount"] == Decimal("50.00")
    
    def test_unbalanced_input(self):
        """Test that unbalanced input raises ValueError."""
        balances = {"A": Decimal("50"), "B": Decimal("-49")}  # Sum = 1, not zero
        with pytest.raises(ValueError, match="Balances not zero-sum"):
            min_cash_flow(balances, tolerance=Decimal("0.01"))
    
    def test_within_tolerance(self):
        """Test that small rounding errors are handled."""
        balances = {"A": Decimal("50.005"), "B": Decimal("-50")}
        # Should not raise, as sum is within default tolerance
        settlements = min_cash_flow(balances, tolerance=Decimal("0.01"))
        assert len(settlements) >= 0  # May be empty or have small settlement
    
    def test_max_iterations_safeguard(self):
        """Test that max_iterations safeguard works."""
        # Create a case that might cause issues (though unlikely in practice)
        balances = {
            "A": Decimal("1000"),
            "B": Decimal("-1000")
        }
        # Should complete in far less than 1000 iterations
        settlements = min_cash_flow(balances, max_iterations=10)
        assert len(settlements) == 1
    
    def test_large_group(self):
        """Test with larger group of users."""
        balances = {
            "A": Decimal("500"),
            "B": Decimal("-100"),
            "C": Decimal("-150"),
            "D": Decimal("-200"),
            "E": Decimal("-50")
        }
        settlements = min_cash_flow(balances)
        
        # Should minimize transactions
        assert len(settlements) <= 4  # Maximum would be 4 if not optimized
        # Verify all debts are settled
        settlement_totals = {}
        for s in settlements:
            from_user = s["from"]
            to_user = s["to"]
            amount = s["amount"]
            settlement_totals[from_user] = settlement_totals.get(from_user, Decimal("0")) - amount
            settlement_totals[to_user] = settlement_totals.get(to_user, Decimal("0")) + amount
        
        for user, balance in balances.items():
            settlement_total = settlement_totals.get(user, Decimal("0"))
            final_balance = balance - settlement_total  # Settlement reduces balance
            assert abs(final_balance) <= Decimal("0.01")


class TestMinCashFlowDetailed:
    """Test the min_cash_flow_detailed function."""
    
    def test_detailed_logging(self):
        """Test that detailed version returns logs."""
        balances = {"A": Decimal("50"), "B": Decimal("-50")}
        settlements, logs = min_cash_flow_detailed(balances)
        
        assert len(settlements) == 1
        assert len(logs) > 0
        assert isinstance(logs, list)
        # Check that logs contain expected information
        log_text = "\n".join(logs)
        assert "Initial balances" in log_text or "balances" in log_text.lower()
    
    def test_log_levels(self):
        """Test different log levels."""
        balances = {"A": Decimal("50"), "B": Decimal("-50")}
        
        for log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            settlements, logs = min_cash_flow_detailed(
                balances,
                log_level=log_level
            )
            assert len(settlements) >= 0
            assert len(logs) > 0


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_full_workflow(self):
        """Test complete workflow from expenses to settlements."""
        expenses = [
            {"payer": "Alice", "amount": Decimal("300"), "participants": ["Alice", "Bob", "Charlie"]},
            {"payer": "Bob", "amount": Decimal("200"), "participants": ["Alice", "Bob"]},
            {"payer": "Charlie", "amount": Decimal("100"), "participants": ["Bob", "Charlie", "David"]},
        ]
        
        # Step 1: Calculate balances
        balances = calculate_balances(expenses)
        
        # Step 2: Validate balances sum to zero
        validate_balance_sum(balances)
        
        # Step 3: Calculate optimized settlements
        settlements = min_cash_flow(balances)
        
        # Step 4: Verify settlements settle all debts
        settlement_totals = {}
        for s in settlements:
            from_user = s["from"]
            to_user = s["to"]
            amount = s["amount"]
            settlement_totals[from_user] = settlement_totals.get(from_user, Decimal("0")) - amount
            settlement_totals[to_user] = settlement_totals.get(to_user, Decimal("0")) + amount
        
        # Final balances should be near zero
        for user, initial_balance in balances.items():
            settlement_total = settlement_totals.get(user, Decimal("0"))
            final_balance = initial_balance - settlement_total  # Settlement reduces balance
            assert abs(final_balance) <= Decimal("0.01"), \
                f"User {user} not settled: initial={initial_balance}, final={final_balance}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

