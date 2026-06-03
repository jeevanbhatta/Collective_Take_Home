"""
Reconciliation Engine Module

This module contains the core business logic to reconcile daily transaction totals 
against reported bank balances. 

Design Decisions & Edge Case Handling for Peer Review:
1. Exact Precision: Used the `Decimal` standard library instead of `float` to avoid 
   IEEE 754 floating-point inaccuracies (e.g., 0.1 + 0.2 = 0.30000000000000004).
2. Missing Dates & Continuity: Interpolates missing dates. If a weekend has no transactions, 
   or the bank fails to report a balance that day, the expected timeline carries forward intact.
3. Multiple Same-Day Transactions: Implicitly groups and sums multiple ledger rows mapping to the same day.
4. Noise Reduction (The "Originating Discrepancy"): Instead of flagging every single day after a mismatch 
   as an error (which creates alert fatigue), it calculates the `new_discrepancy` drift. 
   This directs the accounting team to the exact day the mathematical error occurred.
"""
import csv
from datetime import datetime, timedelta
from decimal import Decimal

def parse_csv_stream(file_stream):
    """
    Utility to parse CSV data uniformly.
    Handles both raw string paths (for CLI/Tests) and byte streams (for Streamlit web uploads).
    """
    if hasattr(file_stream, 'read'):
        content = file_stream.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        import io
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)
    elif isinstance(file_stream, str):
        with open(file_stream, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    return []

def reconcile(transactions_source, balances_source):
    """
    Core business logic. Parses the data, aligns timelines, and calculates variances.
    Returns a unified list of daily records with expected vs actual findings.
    """
    tx_data = parse_csv_stream(transactions_source)
    bb_data = parse_csv_stream(balances_source)
    
    # 1. Aggregate transactions per day
    transactions_by_date = {}
    for row in tx_data:
        date_str = row['date'].strip()
        amount = Decimal(str(row['amount']).strip())
        transactions_by_date[date_str] = transactions_by_date.get(date_str, Decimal('0.0')) + amount
            
    # 2. Map bank balances per day
    bank_balances_by_date = {}
    for row in bb_data:
        date_str = row['date'].strip()
        balance = Decimal(str(row['balance']).strip())
        bank_balances_by_date[date_str] = balance

    if not transactions_by_date and not bank_balances_by_date:
        return []

    # Find the absolute global boundaries of our reporting timeline
    all_dates = set(transactions_by_date.keys()).union(set(bank_balances_by_date.keys()))
    min_date_str = min(all_dates)
    max_date_str = max(all_dates)
    
    start_date = datetime.strptime(min_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(max_date_str, "%Y-%m-%d")

    results = []
    expected_balance = Decimal('0.0')
    last_discrepancy = Decimal('0.0')
    current_date = start_date
    
    # 3. Simulate the ledger step-by-step
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Carry expected balance forward, add any transactions occurring today
        daily_tx_total = transactions_by_date.get(date_str, Decimal('0.0'))
        expected_balance += daily_tx_total
        
        actual_balance = None
        cumulative_discrepancy = None
        new_discrepancy = None
        
        # If the bank generated a statement today, reconcile against it
        if date_str in bank_balances_by_date:
            actual_balance = bank_balances_by_date[date_str]
            cumulative_discrepancy = expected_balance - actual_balance
            
            # Isolate if this discrepancy is new today or carried over from a past date
            new_discrepancy = cumulative_discrepancy - last_discrepancy
            last_discrepancy = cumulative_discrepancy
            
        results.append({
            "date": date_str,
            "transaction_total": float(daily_tx_total),
            "expected_balance": float(expected_balance),
            "actual_balance": float(actual_balance) if actual_balance is not None else None,
            "cumulative_discrepancy": float(cumulative_discrepancy) if cumulative_discrepancy is not None else None,
            "new_discrepancy": float(new_discrepancy) if new_discrepancy is not None else None
        })
            
        current_date += timedelta(days=1)
        
    return results

if __name__ == "__main__":
    # Diagnostic output when executed directly
    res = reconcile("data/sample_provided_tx.csv", "data/sample_provided_bb.csv")
    for r in res:
        if r['new_discrepancy'] and r['new_discrepancy'] != 0.0:
            print(f"Discrepancy Source found on {r['date']}: New Drift of ${r['new_discrepancy']}")
