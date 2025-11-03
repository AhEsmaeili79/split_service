"""
Min-Cash-Flow Algorithm Module

This module implements the Min-Cash-Flow algorithm for minimizing the number of
settlement transactions required to balance group expenses.

The algorithm works by:
1. Calculating net balances for each user (total_paid - total_share)
2. Separating users into creditors (positive balance) and debtors (negative balance)
3. Using a greedy matching strategy to match max creditor with max debtor
4. Minimizing the total number of transactions while ensuring all debts are settled

Time Complexity: O(n log n) for sorting + O(n) for matching = O(n log n)
Space Complexity: O(n) for storing balances and settlement results

Example Usage:
    from app.utils.min_cash_flow import calculate_balances, min_cash_flow
    
    expenses = [
        {"payer": "A", "amount": Decimal("120"), "participants": ["A", "B", "C"]},
        {"payer": "B", "amount": Decimal("60"), "participants": ["B", "C"]},
    ]
    
    balances = calculate_balances(expenses)
    settlements = min_cash_flow(balances)
    
    # Result: [{"from": "C", "to": "A", "amount": Decimal("50.00")}, ...]
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

# Configure logger
logger = logging.getLogger(__name__)


def round_decimal(value: Decimal, precision: Decimal = Decimal('0.01')) -> Decimal:
    """
    Round a Decimal value to the specified precision.
    
    This utility ensures consistent rounding throughout the algorithm,
    preventing floating-point precision issues in financial calculations.
    
    Args:
        value: The Decimal value to round
        precision: The precision to round to (default: 0.01 for cents)
    
    Returns:
        Rounded Decimal value
    
    Example:
        >>> round_decimal(Decimal("43.333333"), Decimal("0.01"))
        Decimal('43.33')
    """
    return value.quantize(precision)


def validate_balance_sum(balances: Dict[str, Decimal], tolerance: Decimal = Decimal('0.01')) -> None:
    """
    Validate that the sum of all balances is approximately zero.
    
    In a correctly balanced expense system, the sum of all net balances
    should equal zero (within rounding tolerance). This ensures no money
    is created or destroyed.
    
    Args:
        balances: Dictionary mapping user_id to net_balance
        tolerance: Maximum allowed deviation from zero (default: 0.01)
    
    Raises:
        ValueError: If the sum of balances exceeds the tolerance
    
    Example:
        >>> balances = {"A": Decimal("50"), "B": Decimal("-50")}
        >>> validate_balance_sum(balances)  # Passes
        >>> balances = {"A": Decimal("50"), "B": Decimal("-49")}
        >>> validate_balance_sum(balances)  # Raises ValueError
    """
    total = sum(balances.values())
    if abs(total) > tolerance:
        raise ValueError(
            f"Balances not zero-sum: total={total}, tolerance={tolerance}. "
            f"This indicates unbalanced expense data."
        )


def calculate_balances(
    expenses: List[Dict],
    tolerance: Decimal = Decimal('0.01')
) -> Dict[str, Decimal]:
    """
    Calculate net balance for each user from a list of expenses.
    
    Net balance = total_paid - total_share
    - Positive balance: User is owed money (creditor)
    - Negative balance: User owes money (debtor)
    
    Supports both equal splits and weighted splits:
    - Equal split: Divide amount equally among all participants
    - Weighted split: Use provided weights (weights must sum to 1.0)
    
    Args:
        expenses: List of expense dictionaries with format:
            {
                "payer": str,              # User who paid
                "amount": Decimal,         # Total expense amount
                "participants": List[str], # Users who share the cost
                "weights": Optional[Dict[str, Decimal]]  # Optional weight per participant
            }
        tolerance: Tolerance for weight sum validation (default: 0.01)
    
    Returns:
        Dictionary mapping user_id -> net_balance (Decimal)
    
    Raises:
        ValueError: If weights are provided but don't sum to 1.0 (within tolerance)
        ValueError: If weights are provided for some participants but not all
    
    Example:
        >>> expenses = [
        ...     {"payer": "A", "amount": Decimal("120"), "participants": ["A", "B", "C"]},
        ...     {"payer": "B", "amount": Decimal("60"), "participants": ["B", "C"]},
        ... ]
        >>> balances = calculate_balances(expenses)
        >>> balances
        {'A': Decimal('80.00'), 'B': Decimal('-10.00'), 'C': Decimal('-70.00')}
    """
    if not expenses:
        return {}
    
    balances: Dict[str, Decimal] = {}
    
    for expense in expenses:
        payer = expense["payer"]
        amount = Decimal(str(expense["amount"]))  # Ensure Decimal
        participants = expense["participants"]
        weights = expense.get("weights")
        
        # Initialize payer balance if not exists
        if payer not in balances:
            balances[payer] = Decimal('0')
        
        # Calculate shares
        if weights:
            # Weighted split
            # Validate weights sum to 1.0
            weight_sum = sum(Decimal(str(w)) for w in weights.values())
            if abs(weight_sum - Decimal('1.0')) > tolerance:
                raise ValueError(
                    f"Weights must sum to 1.0, got {weight_sum}. "
                    f"Expense: {expense.get('title', 'unknown')}"
                )
            
            # Validate all participants have weights
            if set(weights.keys()) != set(participants):
                missing = set(participants) - set(weights.keys())
                raise ValueError(
                    f"All participants must have weights. Missing: {missing}. "
                    f"Expense: {expense.get('title', 'unknown')}"
                )
            
            # Calculate shares based on weights
            for participant in participants:
                if participant not in balances:
                    balances[participant] = Decimal('0')
                
                weight = Decimal(str(weights[participant]))
                share = round_decimal(amount * weight)
                balances[participant] -= share  # Subtract share (what they owe)
        
        else:
            # Equal split
            num_participants = len(participants)
            if num_participants == 0:
                continue
            
            share_per_person = round_decimal(amount / Decimal(str(num_participants)))
            
            for participant in participants:
                if participant not in balances:
                    balances[participant] = Decimal('0')
                
                balances[participant] -= share_per_person  # Subtract share (what they owe)
        
        # Add amount to payer (what they paid)
        balances[payer] = round_decimal(balances[payer] + amount)
    
    # Round all final balances
    balances = {user_id: round_decimal(balance) for user_id, balance in balances.items()}
    
    return balances


def min_cash_flow(
    balances: Dict[str, Decimal],
    tolerance: Decimal = Decimal('0.01'),
    max_iterations: int = 1000,
    strategy: str = "greedy"
) -> List[Dict[str, str]]:
    """
    Minimize the number of transactions needed to settle all debts.
    
    Uses a greedy algorithm that:
    1. Separates users into creditors (positive balance) and debtors (negative balance)
    2. Sorts both lists by absolute amount (largest first)
    3. Iteratively matches max creditor with max debtor
    4. Transfers the minimum of their amounts
    5. Continues until all balances are settled
    
    Edge Cases Handled:
    - If only one user: returns []
    - If all balances are zero (within tolerance): returns []
    - If sum of balances != 0 (beyond tolerance): raises ValueError
    - If max_iterations exceeded: raises RuntimeError (prevents infinite loops)
    
    Args:
        balances: Dictionary mapping user_id -> net_balance
        tolerance: Maximum allowed deviation from zero for validation (default: 0.01)
        max_iterations: Maximum number of iterations to prevent infinite loops (default: 1000)
        strategy: Settlement strategy (default: "greedy", future: "balanced" placeholder)
    
    Returns:
        List of settlement transactions, each with format:
        [{"from": str, "to": str, "amount": Decimal}, ...]
    
    Raises:
        ValueError: If balances don't sum to zero (beyond tolerance)
        RuntimeError: If max_iterations exceeded (rare edge case)
    
    Example:
        >>> balances = {"A": Decimal("80"), "B": Decimal("-10"), "C": Decimal("-70")}
        >>> settlements = min_cash_flow(balances)
        >>> settlements
        [{"from": "C", "to": "A", "amount": Decimal("70.00")},
         {"from": "B", "to": "A", "amount": Decimal("10.00")}]
    """
    # Validate input: sum of balances should be zero
    if not balances:
        return []
    
    # Edge case: only one user
    if len(balances) == 1:
        return []
    
    # Validate balance sum
    validate_balance_sum(balances, tolerance)
    
    # Remove users with zero balance (within tolerance)
    active_balances = {
        user_id: balance
        for user_id, balance in balances.items()
        if abs(balance) > tolerance
    }
    
    # Edge case: all balances are zero
    if not active_balances:
        return []
    
    # Separate into creditors and debtors
    creditors = [
        (user_id, balance)
        for user_id, balance in active_balances.items()
        if balance > tolerance
    ]
    debtors = [
        (user_id, -balance)  # Store as positive for easier matching
        for user_id, balance in active_balances.items()
        if balance < -tolerance
    ]
    
    # Edge case: no creditors or no debtors
    if not creditors or not debtors:
        return []
    
    # Sort by amount (largest first) for greedy matching
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)
    
    settlements = []
    iterations = 0
    
    # Greedy matching algorithm
    i, j = 0, 0
    while i < len(creditors) and j < len(debtors):
        iterations += 1
        
        # Safety check: prevent infinite loops
        if iterations > max_iterations:
            raise RuntimeError(
                f"Settlement loop exceeded max_iterations ({max_iterations}). "
                f"This may indicate malformed input or rounding issues."
            )
        
        creditor_id, credit_amount = creditors[i]
        debtor_id, debt_amount = debtors[j]
        
        # Calculate settlement amount (minimum of credit and debt)
        settlement_amount = min(credit_amount, debt_amount)
        
        # Only create transaction if amount is significant
        if settlement_amount > tolerance:
            settlements.append({
                "from": debtor_id,
                "to": creditor_id,
                "amount": round_decimal(settlement_amount)
            })
        
        # Update balances
        credit_amount = round_decimal(credit_amount - settlement_amount)
        debt_amount = round_decimal(debt_amount - settlement_amount)
        
        creditors[i] = (creditor_id, credit_amount)
        debtors[j] = (debtor_id, debt_amount)
        
        # Advance pointer if balance is settled (within tolerance)
        if credit_amount <= tolerance:
            i += 1
        if debt_amount <= tolerance:
            j += 1
    
    return settlements


def min_cash_flow_detailed(
    balances: Dict[str, Decimal],
    tolerance: Decimal = Decimal('0.01'),
    max_iterations: int = 1000,
    log_level: str = "INFO",
    strategy: str = "greedy"
) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    Minimize transactions with detailed logging of each step.
    
    Same algorithm as min_cash_flow(), but returns detailed logs
    showing the matching process step-by-step. Useful for debugging,
    visualization, and understanding the algorithm workflow.
    
    Args:
        balances: Dictionary mapping user_id -> net_balance
        tolerance: Maximum allowed deviation from zero (default: 0.01)
        max_iterations: Maximum number of iterations (default: 1000)
        log_level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR")
        strategy: Settlement strategy (default: "greedy")
    
    Returns:
        Tuple of (settlements_list, detailed_logs_list)
    
    Example:
        >>> balances = {"A": Decimal("80"), "B": Decimal("-10"), "C": Decimal("-70")}
        >>> settlements, logs = min_cash_flow_detailed(balances, log_level="DEBUG")
        >>> for log in logs:
        ...     print(log)
    """
    # Configure logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    logs = []
    logs.append("=" * 60)
    logs.append("Min-Cash-Flow Algorithm - Detailed Workflow")
    logs.append("=" * 60)
    logs.append(f"Initial balances: {balances}")
    logs.append("")
    
    # Validate input
    if not balances:
        logs.append("No balances provided. Returning empty settlements.")
        return [], logs
    
    if len(balances) == 1:
        logs.append("Only one user. No settlements needed.")
        return [], logs
    
    # Validate balance sum
    try:
        validate_balance_sum(balances, tolerance)
        logs.append(f"✓ Balance validation passed (sum ≈ 0 within tolerance {tolerance})")
    except ValueError as e:
        logs.append(f"✗ Balance validation failed: {e}")
        raise
    
    logs.append("")
    
    # Filter zero balances
    active_balances = {
        user_id: balance
        for user_id, balance in balances.items()
        if abs(balance) > tolerance
    }
    
    if not active_balances:
        logs.append("All balances are zero. No settlements needed.")
        return [], logs
    
    logs.append(f"Active balances (excluding zeros): {active_balances}")
    logs.append("")
    
    # Separate into creditors and debtors
    creditors = [
        (user_id, balance)
        for user_id, balance in active_balances.items()
        if balance > tolerance
    ]
    debtors = [
        (user_id, -balance)
        for user_id, balance in active_balances.items()
        if balance < -tolerance
    ]
    
    logs.append(f"Creditors (to receive): {creditors}")
    logs.append(f"Debtors (to pay): {debtors}")
    logs.append("")
    
    if not creditors or not debtors:
        logs.append("No creditors or no debtors. No settlements possible.")
        return [], logs
    
    # Sort by amount (largest first)
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)
    
    logs.append(f"Sorted creditors: {creditors}")
    logs.append(f"Sorted debtors: {debtors}")
    logs.append("")
    logs.append("Starting greedy matching...")
    logs.append("-" * 60)
    
    settlements = []
    iterations = 0
    
    # Greedy matching algorithm
    i, j = 0, 0
    while i < len(creditors) and j < len(debtors):
        iterations += 1
        
        if iterations > max_iterations:
            error_msg = f"Settlement loop exceeded max_iterations ({max_iterations})"
            logs.append(f"✗ {error_msg}")
            raise RuntimeError(error_msg)
        
        creditor_id, credit_amount = creditors[i]
        debtor_id, debt_amount = debtors[j]
        
        logs.append(f"Step {iterations}: Matching {debtor_id} (debt: {debt_amount}) "
                   f"with {creditor_id} (credit: {credit_amount})")
        
        settlement_amount = min(credit_amount, debt_amount)
        settlement_amount_rounded = round_decimal(settlement_amount)
        
        if settlement_amount > tolerance:
            settlements.append({
                "from": debtor_id,
                "to": creditor_id,
                "amount": settlement_amount_rounded
            })
            logs.append(f"  → Transaction: {debtor_id} pays {creditor_id} "
                       f"${settlement_amount_rounded}")
        else:
            logs.append(f"  → Skipped (amount {settlement_amount} <= tolerance {tolerance})")
        
        # Update balances
        credit_amount = round_decimal(credit_amount - settlement_amount)
        debt_amount = round_decimal(debt_amount - settlement_amount)
        
        creditors[i] = (creditor_id, credit_amount)
        debtors[j] = (debtor_id, debt_amount)
        
        logs.append(f"  Updated balances: {creditor_id}={credit_amount}, {debtor_id}={debt_amount}")
        
        # Advance pointers
        if credit_amount <= tolerance:
            logs.append(f"  → {creditor_id} fully settled, advancing creditor pointer")
            i += 1
        if debt_amount <= tolerance:
            logs.append(f"  → {debtor_id} fully settled, advancing debtor pointer")
            j += 1
        
        logs.append("")
    
    logs.append("-" * 60)
    logs.append(f"Algorithm completed in {iterations} iterations")
    logs.append(f"Total settlements: {len(settlements)}")
    logs.append(f"Final settlements: {settlements}")
    logs.append("=" * 60)
    
    return settlements, logs

