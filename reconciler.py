"""
Reconciliation Engine

Core logic for comparing daily transaction totals against reported bank balances.

A few decisions worth calling out:
- I used Python's `Decimal` type instead of float for all money math. This avoids
  the classic 0.1 + 0.2 != 0.3 floating point issue that would cause false mismatches.
- If a date has no bank statement (weekends, holidays), I just carry the expected
  balance forward and skip the comparison. The timeline stays continuous.
- Multiple transactions on the same day get summed together before comparison.
- The key insight: when a discrepancy happens on Day X, every day after it will
  also show a mismatch. That's just noise. So I track the "new discrepancy" —
  the delta between today's gap and yesterday's gap — to isolate exactly when
  things went wrong.
"""
import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal

def parse_csv_stream(file_stream):
    """
    Reads CSV data from either a file path (string) or an in-memory stream
    (like what Streamlit gives us on file upload). Returns a list of dicts.
    """
    if hasattr(file_stream, 'read'):
        content = file_stream.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)
    elif isinstance(file_stream, str):
        with open(file_stream, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    return []

def reconcile(transactions_source, balances_source):
    """
    Main reconciliation function. Takes two CSV sources (paths or streams),
    walks through every day in the range, and compares what we expect the
    balance to be vs what the bank actually reported.

    Returns a list of daily records. Each record includes:
    - expected_balance: running sum of all transactions up to that day
    - actual_balance: what the bank said (None if no statement that day)
    - cumulative_discrepancy: total gap between expected and actual
    - new_discrepancy: how much of that gap is NEW today (the useful part)

    Note on the float conversion at the end: I do all the math in Decimal
    for precision, but convert to float in the output dict. This is because
    pandas/plotly/streamlit all expect regular floats, and by this point
    the precision-sensitive calculations are done. The conversion happens
    once, at the boundary, not during arithmetic.
    """
    tx_data = parse_csv_stream(transactions_source)
    bb_data = parse_csv_stream(balances_source)
    
    # Group and sum transactions by date
    transactions_by_date = {}
    for row in tx_data:
        date_str = row['date'].strip()
        amount = Decimal(str(row['amount']).strip())
        transactions_by_date[date_str] = transactions_by_date.get(date_str, Decimal('0.0')) + amount
            
    # Map bank balances by date
    bank_balances_by_date = {}
    for row in bb_data:
        date_str = row['date'].strip()
        balance = Decimal(str(row['balance']).strip())
        bank_balances_by_date[date_str] = balance

    if not transactions_by_date and not bank_balances_by_date:
        return []

    # Figure out the full date range we need to cover
    all_dates = set(transactions_by_date.keys()).union(set(bank_balances_by_date.keys()))
    min_date_str = min(all_dates)
    max_date_str = max(all_dates)
    
    start_date = datetime.strptime(min_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(max_date_str, "%Y-%m-%d")

    results = []
    expected_balance = Decimal('0.0')
    last_discrepancy = Decimal('0.0')
    current_date = start_date
    
    # Walk through every calendar day, even if nothing happened
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Add today's transactions (if any) to the running total
        daily_tx_total = transactions_by_date.get(date_str, Decimal('0.0'))
        expected_balance += daily_tx_total
        
        actual_balance = None
        cumulative_discrepancy = None
        new_discrepancy = None
        
        # Only compare if the bank actually reported a balance today
        if date_str in bank_balances_by_date:
            actual_balance = bank_balances_by_date[date_str]
            cumulative_discrepancy = expected_balance - actual_balance
            
            # This is the important bit: did things get *worse* today,
            # or is this just yesterday's error carrying forward?
            new_discrepancy = cumulative_discrepancy - last_discrepancy
            last_discrepancy = cumulative_discrepancy
        
        # Convert Decimal -> float at the output boundary.
        # All the precision-sensitive math is already done above.
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
    # Quick sanity check when running this file directly
    res = reconcile("data/sample_provided_tx.csv", "data/sample_provided_bb.csv")
    for r in res:
        if r['new_discrepancy'] and r['new_discrepancy'] != 0.0:
            print(f"Discrepancy found on {r['date']}: New drift of ${r['new_discrepancy']}")
