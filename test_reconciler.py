"""
Tests for the reconciliation engine.

Covers the main edge cases I thought about: missing weekend data,
floating point precision traps, out-of-order CSVs, multiple same-day
transactions, and discrepancy isolation (the "noise reduction" logic).

I use io.StringIO for the base case to also verify that the engine
handles in-memory streams (which is how Streamlit passes uploaded files).
The rest read from actual CSV fixtures in data/ for realism.
"""
import unittest
import io
from reconciler import reconcile

class TestReconciler(unittest.TestCase):
    
    def test_clean_reconciliation_buffer(self):
        """
        Base case: two days, numbers match perfectly.
        Also doubles as a check that StringIO streams work (needed for Streamlit uploads).
        """
        tx_csv = "date,amount\n2025-06-01,1000.00\n2025-06-02,-50.00"
        bb_csv = "date,balance\n2025-06-01,1000.00\n2025-06-02,950.00"
        
        discrepancies = reconcile(io.StringIO(tx_csv), io.StringIO(bb_csv))
        
        for row in discrepancies:
            if row['actual_balance'] is not None:
                self.assertEqual(row['new_discrepancy'], 0.0)

    def test_isolate_origin_discrepancy(self):
        """
        If a $50 error happens on Day 2, then Days 3 and 4 will also show
        a cumulative mismatch — but no NEW drift. The engine should only
        flag Day 2 as the originating problem.
        """
        discrepancies = reconcile("data/edge_case_discrepancy_tx.csv", "data/edge_case_discrepancy_bb.csv")
        
        day_2 = [r for r in discrepancies if r['date'] == '2025-06-02'][0]
        self.assertEqual(day_2['new_discrepancy'], 50.0) # Expected 450, Actual 400. Gap = 50.
        
        day_3 = [r for r in discrepancies if r['date'] == '2025-06-03'][0]
        self.assertEqual(day_3['new_discrepancy'], 0.0) # Gap is still 50, but nothing new.

    def test_missing_weekend_data(self):
        """
        Bank reports on Friday and Monday, but not Sat/Sun.
        Transactions still happen over the weekend though.
        The engine should carry balances forward through the gap.
        """
        discrepancies = reconcile("data/edge_case_weekends_tx.csv", "data/edge_case_weekends_bb.csv")
        
        # Friday: should reconcile cleanly
        day_fri = [r for r in discrepancies if r['date'] == '2025-06-06'][0]
        self.assertEqual(day_fri['new_discrepancy'], 0.0)
        
        # Saturday: transactions happened, but bank didn't report
        day_sat = [r for r in discrepancies if r['date'] == '2025-06-07'][0]
        self.assertIsNone(day_sat['actual_balance'])
        self.assertEqual(day_sat['expected_balance'], 90.0)
        
        # Monday: everything should catch back up
        day_mon = [r for r in discrepancies if r['date'] == '2025-06-09'][0]
        self.assertEqual(day_mon['new_discrepancy'], 0.0)

    def test_floating_point_precision(self):
        """
        Classic trap: 0.10 + 0.20 = 0.30000000000000004 in normal floats.
        Since I'm using Decimal internally, this should reconcile to exactly 0.
        """
        discrepancies = reconcile("data/edge_case_precision_tx.csv", "data/edge_case_precision_bb.csv")
        
        day_2 = [r for r in discrepancies if r['date'] == '2025-06-02'][0]
        self.assertEqual(day_2['new_discrepancy'], 0.0)

    def test_out_of_order_and_multiple_same_day(self):
        """
        CSVs aren't chronologically sorted, and there are multiple
        transactions on the same day. Engine should handle both gracefully.
        """
        discrepancies = reconcile("data/edge_case_outoforder_tx.csv", "data/edge_case_outoforder_bb.csv")
        
        # Should cover 3 days total
        self.assertEqual(len(discrepancies), 3)
        self.assertEqual(discrepancies[0]['date'], '2025-06-01')
        self.assertEqual(discrepancies[-1]['date'], '2025-06-03')
        
        # Everything should reconcile perfectly
        for row in discrepancies:
            self.assertEqual(row['new_discrepancy'], 0.0)

    def test_sample_provided_data_reconciles(self):
        """
        Sanity check: the sample data from the assignment prompt should
        reconcile with zero discrepancies across all 12 days.
        """
        results = reconcile("data/sample_provided_tx.csv", "data/sample_provided_bb.csv")
        
        self.assertEqual(len(results), 12)
        for row in results:
            if row['actual_balance'] is not None:
                self.assertEqual(row['new_discrepancy'], 0.0,
                    f"Unexpected discrepancy on {row['date']}")

    def test_sample_mismatch_isolates_errors(self):
        """
        The mismatch sample has two deliberate bank errors:
        - A $50 gap starting on 06-03 (bank underreported)
        - An additional $5 gap on 06-10

        The engine should flag exactly those two days as originating
        discrepancies, and all other days should show new_discrepancy = 0.
        """
        results = reconcile("data/sample_mismatch_tx.csv", "data/sample_mismatch_bb.csv")

        # Collect only the days where new drift was introduced
        origin_days = [r for r in results 
                       if r['new_discrepancy'] is not None and r['new_discrepancy'] != 0.0]
        
        self.assertEqual(len(origin_days), 2, 
            f"Expected exactly 2 originating discrepancies, got {len(origin_days)}")
        
        # First error: 06-03, bank reports 675 instead of 725 = $50 gap
        self.assertEqual(origin_days[0]['date'], '2025-06-03')
        self.assertEqual(origin_days[0]['new_discrepancy'], 50.0)
        
        # Second error: 06-10, bank reports 660 instead of 715 = additional $5
        self.assertEqual(origin_days[1]['date'], '2025-06-10')
        self.assertEqual(origin_days[1]['new_discrepancy'], 5.0)
        
        # All other days with bank data should have zero new drift
        carry_days = [r for r in results 
                      if r['new_discrepancy'] is not None and r['new_discrepancy'] == 0.0]
        self.assertEqual(len(carry_days), 10)  # 12 days total, 2 are origins

if __name__ == '__main__':
    unittest.main()
