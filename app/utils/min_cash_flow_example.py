"""
Example Module for Min-Cash-Flow Algorithm

This module provides example simulations and demonstrations of the
Min-Cash-Flow algorithm with various expense scenarios.

Run this module directly to see the algorithm in action:
    python -m app.utils.min_cash_flow_example
"""

from decimal import Decimal
from typing import List, Dict
from app.utils.min_cash_flow import (
    calculate_balances,
    min_cash_flow,
    min_cash_flow_detailed
)


def run_example_equal_split():
    """Example with equal split expenses."""
    print("\n" + "=" * 70)
    print("Example 1: Equal Split Expenses")
    print("=" * 70)
    
    expenses = [
        {"payer": "A", "amount": Decimal("120"), "participants": ["A", "B", "C"]},
        {"payer": "B", "amount": Decimal("60"), "participants": ["B", "C"]},
        {"payer": "C", "amount": Decimal("40"), "participants": ["A", "C", "D"]},
    ]
    
    print("\nExpenses:")
    for i, expense in enumerate(expenses, 1):
        print(f"  {i}. {expense['payer']} paid ${expense['amount']} split equally among "
              f"{expense['participants']}")
    
    # Calculate balances
    balances = calculate_balances(expenses)
    
    print("\nNet Balances (total_paid - total_share):")
    for user, balance in sorted(balances.items()):
        status = "owed" if balance > 0 else "owes"
        print(f"  {user}: ${abs(balance):.2f} ({status})")
    
    # Calculate optimized settlements
    settlements, logs = min_cash_flow_detailed(balances, log_level="INFO")
    
    print("\nDetailed Workflow:")
    print("\n".join(logs))
    
    print("\nFinal Optimized Settlements:")
    if settlements:
        for i, settlement in enumerate(settlements, 1):
            print(f"  {i}. {settlement['from']} → {settlement['to']}: "
                  f"${settlement['amount']:.2f}")
    else:
        print("  No settlements needed (all balances are zero)")
    
    print(f"\nTotal transactions: {len(settlements)}")
    print("=" * 70)


def run_example_weighted_split():
    """Example with weighted split expenses."""
    print("\n" + "=" * 70)
    print("Example 2: Weighted Split Expenses")
    print("=" * 70)
    
    expenses = [
        {
            "payer": "Alice",
            "amount": Decimal("300"),
            "participants": ["Alice", "Bob", "Charlie"],
            "weights": {
                "Alice": Decimal("0.5"),   # Pays 50%
                "Bob": Decimal("0.3"),     # Pays 30%
                "Charlie": Decimal("0.2")  # Pays 20%
            }
        },
        {
            "payer": "Bob",
            "amount": Decimal("100"),
            "participants": ["Alice", "Bob"],
            "weights": {
                "Alice": Decimal("0.6"),
                "Bob": Decimal("0.4")
            }
        }
    ]
    
    print("\nExpenses:")
    for i, expense in enumerate(expenses, 1):
        print(f"\n  {i}. {expense['payer']} paid ${expense['amount']}")
        print(f"     Participants: {expense['participants']}")
        if 'weights' in expense:
            print(f"     Weights: {expense['weights']}")
            for participant, weight in expense['weights'].items():
                share = expense['amount'] * weight
                print(f"       {participant}: {weight * 100}% = ${share:.2f}")
    
    # Calculate balances
    balances = calculate_balances(expenses)
    
    print("\nNet Balances:")
    for user, balance in sorted(balances.items()):
        status = "owed" if balance > 0 else "owes"
        print(f"  {user}: ${abs(balance):.2f} ({status})")
    
    # Calculate optimized settlements
    settlements = min_cash_flow(balances)
    
    print("\nOptimized Settlements:")
    if settlements:
        for i, settlement in enumerate(settlements, 1):
            print(f"  {i}. {settlement['from']} → {settlement['to']}: "
                  f"${settlement['amount']:.2f}")
    else:
        print("  No settlements needed")
    
    print(f"\nTotal transactions: {len(settlements)}")
    print("=" * 70)


def run_example_large_group():
    """Example with a larger group (10 users)."""
    print("\n" + "=" * 70)
    print("Example 3: Large Group (10 users, 5 expenses)")
    print("=" * 70)
    
    expenses = [
        {"payer": "User1", "amount": Decimal("500"), "participants": ["User1", "User2", "User3"]},
        {"payer": "User2", "amount": Decimal("300"), "participants": ["User2", "User4", "User5"]},
        {"payer": "User3", "amount": Decimal("200"), "participants": ["User1", "User3", "User6"]},
        {"payer": "User4", "amount": Decimal("150"), "participants": ["User4", "User7", "User8"]},
        {"payer": "User5", "amount": Decimal("100"), "participants": ["User5", "User9", "User10"]},
    ]
    
    print(f"\nExpenses: {len(expenses)} expenses with 10 total users")
    
    # Calculate balances
    balances = calculate_balances(expenses)
    
    print("\nNet Balances:")
    creditors = {u: b for u, b in balances.items() if b > Decimal('0.01')}
    debtors = {u: b for u, b in balances.items() if b < Decimal('-0.01')}
    
    print(f"  Creditors: {len(creditors)} users")
    print(f"  Debtors: {len(debtors)} users")
    print(f"  Zero balance: {len(balances) - len(creditors) - len(debtors)} users")
    
    # Calculate optimized settlements
    settlements = min_cash_flow(balances)
    
    print("\nOptimized Settlements:")
    print(f"  Total transactions needed: {len(settlements)}")
    print(f"  (Without optimization, would need up to {len(creditors) * len(debtors)} transactions)")
    
    if settlements:
        print("\n  Transaction details:")
        for i, settlement in enumerate(settlements, 1):
            print(f"    {i}. {settlement['from']} → {settlement['to']}: "
                  f"${settlement['amount']:.2f}")
    
    print("=" * 70)


def run_example_edge_cases():
    """Example demonstrating edge cases."""
    print("\n" + "=" * 70)
    print("Example 4: Edge Cases")
    print("=" * 70)
    
    # Edge case 1: Single user
    print("\n1. Single User Test:")
    balances_single = {"A": Decimal("0")}
    settlements_single = min_cash_flow(balances_single)
    print(f"   Balances: {balances_single}")
    print(f"   Settlements: {settlements_single} (expected: empty)")
    
    # Edge case 2: All zero balances
    print("\n2. All Zero Balances Test:")
    balances_zero = {"A": Decimal("0"), "B": Decimal("0"), "C": Decimal("0")}
    settlements_zero = min_cash_flow(balances_zero)
    print(f"   Balances: {balances_zero}")
    print(f"   Settlements: {settlements_zero} (expected: empty)")
    
    # Edge case 3: Perfectly balanced
    print("\n3. Perfectly Balanced Test:")
    expenses_balanced = [
        {"payer": "A", "amount": Decimal("100"), "participants": ["A", "B"]},
        {"payer": "B", "amount": Decimal("100"), "participants": ["A", "B"]},
    ]
    balances_balanced = calculate_balances(expenses_balanced)
    settlements_balanced = min_cash_flow(balances_balanced)
    print(f"   Balances: {balances_balanced}")
    print(f"   Settlements: {settlements_balanced} (expected: empty)")
    
    print("=" * 70)


def main():
    """Run all examples."""
    print("\n" + "🔢" * 35)
    print("Min-Cash-Flow Algorithm - Example Demonstrations")
    print("🔢" * 35)
    
    try:
        run_example_equal_split()
        run_example_weighted_split()
        run_example_large_group()
        run_example_edge_cases()
        
        print("\n" + "✅" * 35)
        print("All examples completed successfully!")
        print("✅" * 35 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

