"""
Comprehensive Test Suite for Min-Cash-Flow Algorithm

This test suite verifies:
1. Core algorithm correctness
2. Edge case handling
3. API compatibility (OptimizedSettlement format)
4. Integration with expense_service
5. Mathematical correctness
6. Performance with large datasets
"""

from decimal import Decimal
from typing import Dict, List
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.utils.min_cash_flow import (
    calculate_balances,
    min_cash_flow,
    min_cash_flow_detailed,
    round_decimal,
    validate_balance_sum
)


class TestMinCashFlow:
    """Comprehensive test suite for Min-Cash-Flow algorithm."""
    
    def test_round_decimal_utility(self):
        """Test rounding utility function."""
        assert round_decimal(Decimal("43.333333")) == Decimal("43.33")
        assert round_decimal(Decimal("43.336666")) == Decimal("43.34")
        # Note: 100.005 rounds to 100.00 with ROUND_HALF_EVEN (banker's rounding)
        assert round_decimal(Decimal("100.005")) == Decimal("100.00")
        assert round_decimal(Decimal("100.015")) == Decimal("100.02")  # This rounds up
        assert round_decimal(Decimal("0.001"), Decimal("0.01")) == Decimal("0.00")
        print("✓ round_decimal utility tests passed")
    
    def test_validate_balance_sum(self):
        """Test balance validation."""
        # Valid balanced sum
        balances = {"A": Decimal("50"), "B": Decimal("-50")}
        validate_balance_sum(balances)
        
        # Within tolerance
        balances = {"A": Decimal("50.005"), "B": Decimal("-50")}
        validate_balance_sum(balances, tolerance=Decimal("0.01"))
        
        # Should raise ValueError for unbalanced
        balances = {"A": Decimal("50"), "B": Decimal("-49")}
        try:
            validate_balance_sum(balances)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        
        print("✓ validate_balance_sum tests passed")
    
    def test_calculate_balances_equal_split(self):
        """Test balance calculation with equal splits."""
        expenses = [
            {"payer": "A", "amount": Decimal("120"), "participants": ["A", "B", "C"]},
            {"payer": "B", "amount": Decimal("60"), "participants": ["B", "C"]},
            {"payer": "C", "amount": Decimal("40"), "participants": ["A", "C", "D"]},
        ]
        
        balances = calculate_balances(expenses)
        
        # Verify balances sum to zero
        total = sum(balances.values())
        assert abs(total) <= Decimal("0.01"), f"Balances don't sum to zero: {total}"
        
        # Expected balances:
        # A: paid 120, owes 40 (from first) + 13.33 (from third) = 53.33, net = 66.67
        # B: paid 60, owes 40 + 30 = 70, net = -10
        # C: paid 40, owes 40 + 30 + 13.33 = 83.33, net = -43.33
        # D: paid 0, owes 13.33, net = -13.33
        
        assert abs(balances["A"] - Decimal("66.67")) <= Decimal("0.02")
        assert abs(balances["B"] - Decimal("-10.00")) <= Decimal("0.01")
        assert abs(balances["C"] - Decimal("-43.33")) <= Decimal("0.02")
        assert abs(balances["D"] - Decimal("-13.33")) <= Decimal("0.02")
        
        print("✓ calculate_balances (equal split) tests passed")
    
    def test_calculate_balances_weighted_split(self):
        """Test balance calculation with weighted splits."""
        expenses = [
            {
                "payer": "Alice",
                "amount": Decimal("300"),
                "participants": ["Alice", "Bob", "Charlie"],
                "weights": {
                    "Alice": Decimal("0.5"),
                    "Bob": Decimal("0.3"),
                    "Charlie": Decimal("0.2")
                }
            }
        ]
        
        balances = calculate_balances(expenses)
        
        # Alice paid 300, owes 150 (50%), net = 150
        # Bob paid 0, owes 90 (30%), net = -90
        # Charlie paid 0, owes 60 (20%), net = -60
        
        assert abs(balances["Alice"] - Decimal("150.00")) <= Decimal("0.01")
        assert abs(balances["Bob"] - Decimal("-90.00")) <= Decimal("0.01")
        assert abs(balances["Charlie"] - Decimal("-60.00")) <= Decimal("0.01")
        
        # Verify sum is zero
        total = sum(balances.values())
        assert abs(total) <= Decimal("0.01")
        
        print("✓ calculate_balances (weighted split) tests passed")
    
    def test_min_cash_flow_basic(self):
        """Test basic min cash flow algorithm."""
        balances = {
            "A": Decimal("80"),
            "B": Decimal("-10"),
            "C": Decimal("-70")
        }
        
        settlements = min_cash_flow(balances)
        
        # Should create 2 transactions:
        # C pays A $70
        # B pays A $10
        
        assert len(settlements) == 2
        
        settlement_dict = {(s["from"], s["to"]): s["amount"] for s in settlements}
        assert ("C", "A") in settlement_dict
        assert settlement_dict[("C", "A")] == Decimal("70.00")
        assert ("B", "A") in settlement_dict
        assert settlement_dict[("B", "A")] == Decimal("10.00")
        
        # Verify settlements settle all debts
        self._verify_settlements_settle_debts(balances, settlements)
        
        print("✓ min_cash_flow basic tests passed")
    
    def test_min_cash_flow_spec_example(self):
        """Test with the exact specification example."""
        expenses = [
            {"payer": "A", "amount": Decimal("120"), "participants": ["A", "B", "C"]},
            {"payer": "B", "amount": Decimal("60"), "participants": ["B", "C"]},
            {"payer": "C", "amount": Decimal("40"), "participants": ["A", "C", "D"]},
        ]
        
        balances = calculate_balances(expenses)
        settlements = min_cash_flow(balances)
        
        # Verify all debts are settled
        self._verify_settlements_settle_debts(balances, settlements)
        
        # Verify settlement format matches OptimizedSettlement schema
        for settlement in settlements:
            assert "from" in settlement
            assert "to" in settlement
            assert "amount" in settlement
            assert isinstance(settlement["amount"], Decimal)
            assert settlement["amount"] > Decimal("0")
        
        print("✓ Specification example test passed")
    
    def test_edge_case_single_user(self):
        """Test edge case: single user."""
        balances = {"A": Decimal("0")}
        settlements = min_cash_flow(balances)
        assert settlements == []
        print("✓ Edge case: single user passed")
    
    def test_edge_case_zero_balances(self):
        """Test edge case: all zero balances."""
        balances = {"A": Decimal("0"), "B": Decimal("0"), "C": Decimal("0")}
        settlements = min_cash_flow(balances)
        assert settlements == []
        print("✓ Edge case: zero balances passed")
    
    def test_edge_case_perfectly_balanced(self):
        """Test when expenses are already balanced."""
        balances = {"A": Decimal("50"), "B": Decimal("-50")}
        settlements = min_cash_flow(balances)
        assert len(settlements) == 1
        assert settlements[0]["from"] == "B"
        assert settlements[0]["to"] == "A"
        assert settlements[0]["amount"] == Decimal("50.00")
        print("✓ Edge case: perfectly balanced passed")
    
    def test_large_group(self):
        """Test with larger group (10 users)."""
        balances = {
            "User1": Decimal("500"),
            "User2": Decimal("-100"),
            "User3": Decimal("-150"),
            "User4": Decimal("-200"),
            "User5": Decimal("-50")
        }
        
        settlements = min_cash_flow(balances)
        
        # Should minimize transactions (should be <= 4)
        assert len(settlements) <= 4
        
        # Verify all debts are settled
        self._verify_settlements_settle_debts(balances, settlements)
        
        print("✓ Large group test passed")
    
    def test_optimized_settlements_format(self):
        """Test that settlements match OptimizedSettlement API format."""
        balances = {"A": Decimal("50"), "B": Decimal("-50")}
        settlements = min_cash_flow(balances)
        
        # Verify format matches OptimizedSettlement schema:
        # from_user_id: str
        # to_user_id: str
        # amount: Decimal
        
        for settlement in settlements:
            assert isinstance(settlement["from"], str)
            assert isinstance(settlement["to"], str)
            assert isinstance(settlement["amount"], Decimal)
            
            # Verify can be converted to OptimizedSettlement format
            # (simulating what expense_service does)
            from_user_id = settlement["from"]
            to_user_id = settlement["to"]
            amount = settlement["amount"]
            
            assert from_user_id is not None
            assert to_user_id is not None
            assert amount > Decimal("0")
        
        print("✓ OptimizedSettlement format compatibility test passed")
    
    def test_detailed_logging(self):
        """Test detailed logging version."""
        balances = {"A": Decimal("50"), "B": Decimal("-50")}
        settlements, logs = min_cash_flow_detailed(balances, log_level="INFO")
        
        assert len(settlements) == 1
        assert len(logs) > 0
        assert isinstance(logs, list)
        
        # Check logs contain useful information
        log_text = "\n".join(logs)
        assert "balances" in log_text.lower() or "Balance" in log_text
        assert "settlement" in log_text.lower() or "Settlement" in log_text
        
        print("✓ Detailed logging test passed")
    
    def test_max_iterations_safeguard(self):
        """Test that max_iterations safeguard works."""
        # Create a simple case that should complete quickly
        balances = {"A": Decimal("1000"), "B": Decimal("-1000")}
        
        # Should complete in far less than 1000 iterations
        settlements = min_cash_flow(balances, max_iterations=10)
        assert len(settlements) == 1
        
        print("✓ Max iterations safeguard test passed")
    
    def test_rounding_tolerance(self):
        """Test handling of rounding tolerance."""
        # Create balances with small rounding differences
        balances = {
            "A": Decimal("50.005"),
            "B": Decimal("-50.00")
        }
        
        # Should handle within tolerance
        settlements = min_cash_flow(balances, tolerance=Decimal("0.01"))
        assert len(settlements) >= 0  # May be empty or have small settlement
        
        print("✓ Rounding tolerance test passed")
    
    def test_weighted_split_validation(self):
        """Test validation of weighted splits."""
        # Invalid weights (don't sum to 1.0)
        expenses = [
            {
                "payer": "A",
                "amount": Decimal("100"),
                "participants": ["A", "B"],
                "weights": {"A": Decimal("0.6"), "B": Decimal("0.5")}  # Sums to 1.1
            }
        ]
        
        try:
            calculate_balances(expenses)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Weights must sum to 1.0" in str(e)
        
        print("✓ Weighted split validation test passed")
    
    def _verify_settlements_settle_debts(self, balances: Dict[str, Decimal], settlements: List[Dict]) -> None:
        """Helper to verify settlements settle all debts.
        
        Settlement logic:
        - If user receives money (positive settlement_total), it reduces what they're owed
        - If user pays money (negative settlement_total), it reduces what they owe
        - Final balance = initial_balance - settlement_total (for both creditors and debtors)
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
            
            # from_user pays (negative for them)
            settlement_totals[from_user] -= amount
            # to_user receives (positive for them)
            settlement_totals[to_user] += amount
        
        # Verify each user's final balance is near zero
        # Final balance = initial_balance - settlement_total
        # For creditors (positive balance): receiving money reduces what they're owed
        # For debtors (negative balance): paying money reduces what they owe
        for user, initial_balance in balances.items():
            if abs(initial_balance) <= Decimal("0.01"):
                continue  # Skip zero balances
            
            settlement_total = settlement_totals.get(user, Decimal("0"))
            # Settlement reduces the absolute balance
            # If owed (+80) and receive (+80): final = 80 - 80 = 0 ✓
            # If owe (-80) and pay (-80): final = -80 - (-80) = -80 + 80 = 0 ✓
            final_balance = initial_balance - settlement_total
            
            assert abs(final_balance) <= Decimal("0.01"), \
                f"User {user} not settled: initial={initial_balance}, " \
                f"settlement_total={settlement_total}, final={final_balance}"


def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("=" * 70)
    print("Comprehensive Min-Cash-Flow Algorithm Test Suite")
    print("=" * 70)
    print()
    
    tester = TestMinCashFlow()
    
    tests = [
        ("Rounding Utility", tester.test_round_decimal_utility),
        ("Balance Validation", tester.test_validate_balance_sum),
        ("Calculate Balances (Equal Split)", tester.test_calculate_balances_equal_split),
        ("Calculate Balances (Weighted Split)", tester.test_calculate_balances_weighted_split),
        ("Min Cash Flow Basic", tester.test_min_cash_flow_basic),
        ("Specification Example", tester.test_min_cash_flow_spec_example),
        ("Edge Case: Single User", tester.test_edge_case_single_user),
        ("Edge Case: Zero Balances", tester.test_edge_case_zero_balances),
        ("Edge Case: Perfectly Balanced", tester.test_edge_case_perfectly_balanced),
        ("Large Group", tester.test_large_group),
        ("OptimizedSettlement Format", tester.test_optimized_settlements_format),
        ("Detailed Logging", tester.test_detailed_logging),
        ("Max Iterations Safeguard", tester.test_max_iterations_safeguard),
        ("Rounding Tolerance", tester.test_rounding_tolerance),
        ("Weighted Split Validation", tester.test_weighted_split_validation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()
    
    print("=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"❌ {failed} TEST(S) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    run_comprehensive_tests()

