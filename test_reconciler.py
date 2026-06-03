"""
Test Suite for Reconciliation Engine

Coverage includes edge cases requested in the prompt: missing boundary data, 
simulated floating point limits, and strict discrepancy isolation.

By wrapping our mock test data in `io.StringIO`, we simultaneously verify that 
the engine supports decoupled byte streams (which Streamlit requires to process 
uploaded files without saving them to disk). We also test directly using the 
generated edge case CSVs from the data/ folder.
"""
import unittest
import io
from reconciler import reconcile

class TestReconciler(unittest.TestCase):
    
    def test_clean_reconciliation_buffer(self):
        """
        Base Case: Verifies that matched numbers correctly result in exactly
        zero new discrepancies across the timeline using string buffers.
        """
        tx_csv = "date,amount\n2025-06-01,1000.00\n2025-06-02,-50.00"
        bb_csv = "date,balance\n2025-06-01,1000.00\n2025-06-02,950.00"
        
        discrepancies = reconcile(io.StringIO(tx_csv), io.StringIO(bb_csv))
        
        for row in discrepancies:
            if row['actual_balance'] is not None:
                self.assertEqual(row['new_discrepancy'], 0.0)

    def test_isolate_origin_discrepancy(self):
        """
        Edge Case (Noise Reduction): 
        If a $50 error happens on Day 2, the total running balance on Days 3 and 4 
        will also be wrong. This tests that our engine flags Day 2 as the Origin 
        Point, leaving Days 3 and 4 with a `new_discrepancy` of 0.0.
        Reads from data/edge_case_discrepancy_*.csv explicitly.
        """
        discrepancies = reconcile("data/edge_case_discrepancy_tx.csv", "data/edge_case_discrepancy_bb.csv")
        
        day_2 = [r for r in discrepancies if r['date'] == '2025-06-02'][0]
        self.assertEqual(day_2['new_discrepancy'], 50.0) # Expected 450, Actual 400. Gap = 50.
        
        day_3 = [r for r in discrepancies if r['date'] == '2025-06-03'][0]
        self.assertEqual(day_3['new_discrepancy'], 0.0) # Expected 430, Actual 380. Gap = 50. New Drift = 0!

    def test_missing_weekend_data(self):
        """
        Edge Case: Bank records stop on Friday (06-06) and resume Monday (06-09).
        Transactions happen over the weekend.
        Ensures the timeline iterates continuously and balances carry forward implicitly.
        """
        discrepancies = reconcile("data/edge_case_weekends_tx.csv", "data/edge_case_weekends_bb.csv")
        
        # Friday: Expected 100, Actual 100
        day_fri = [r for r in discrepancies if r['date'] == '2025-06-06'][0]
        self.assertEqual(day_fri['new_discrepancy'], 0.0)
        
        # Saturday and Sunday: Have expected balances but actual_balance should be None
        day_sat = [r for r in discrepancies if r['date'] == '2025-06-07'][0]
        self.assertIsNone(day_sat['actual_balance'])
        self.assertEqual(day_sat['expected_balance'], 90.0)
        
        # Monday: Expected 70, Actual 70
        day_mon = [r for r in discrepancies if r['date'] == '2025-06-09'][0]
        self.assertEqual(day_mon['new_discrepancy'], 0.0)

    def test_floating_point_precision(self):
        """
        Edge Case: 0.10 + 0.20 = 0.30000000000000004 in normal Python floats.
        Ensures our engine strictly matches 0.30 using Decimal without triggering 
        a false micro-discrepancy.
        """
        discrepancies = reconcile("data/edge_case_precision_tx.csv", "data/edge_case_precision_bb.csv")
        
        day_2 = [r for r in discrepancies if r['date'] == '2025-06-02'][0]
        self.assertEqual(day_2['new_discrepancy'], 0.0)

    def test_out_of_order_and_multiple_same_day(self):
        """
        Edge Case: The transaction and bank CSVs are not chronically sorted, and 
        there are multiple transactions occurring on the exact same day.
        Ensures the parser properly groups, sums, and sorts before calculating.
        """
        discrepancies = reconcile("data/edge_case_outoforder_tx.csv", "data/edge_case_outoforder_bb.csv")
        
        # Total dates range from 01 to 03
        self.assertEqual(len(discrepancies), 3)
        self.assertEqual(discrepancies[0]['date'], '2025-06-01')
        self.assertEqual(discrepancies[-1]['date'], '2025-06-03')
        
        # All days should perfectly reconcile to 0 new_discrepancy
        for row in discrepancies:
            self.assertEqual(row['new_discrepancy'], 0.0)

if __name__ == '__main__':
    unittest.main()
