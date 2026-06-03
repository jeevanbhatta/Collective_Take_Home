"""
Tests for the reconciliation engine.
Uses StringIO for the base case to also check that in-memory streams work (Streamlit uploads).
The rest read from CSV fixtures in data/.
"""
import unittest
import io
from reconciler import reconcile

class TestReconciler(unittest.TestCase):
    
    def test_clean_reconciliation_buffer(self):
        tx_csv = "date,amount\n2025-06-01,1000.00\n2025-06-02,-50.00"
        bb_csv = "date,balance\n2025-06-01,1000.00\n2025-06-02,950.00"
        
        results = reconcile(io.StringIO(tx_csv), io.StringIO(bb_csv))
        
        for row in results:
            if row['actual_balance'] is not None:
                self.assertEqual(row['new_discrepancy'], 0.0)

    def test_isolate_origin_discrepancy(self):
        # $50 error on day 2 should be flagged; day 3 just carries it forward
        results = reconcile("data/edge_case_discrepancy_tx.csv", "data/edge_case_discrepancy_bb.csv")
        
        day_2 = [r for r in results if r['date'] == '2025-06-02'][0]
        self.assertEqual(day_2['new_discrepancy'], 50.0)
        
        day_3 = [r for r in results if r['date'] == '2025-06-03'][0]
        self.assertEqual(day_3['new_discrepancy'], 0.0)

    def test_missing_weekend_data(self):
        results = reconcile("data/edge_case_weekends_tx.csv", "data/edge_case_weekends_bb.csv")
        
        day_fri = [r for r in results if r['date'] == '2025-06-06'][0]
        self.assertEqual(day_fri['new_discrepancy'], 0.0)
        
        # Sat has transactions but no bank statement
        day_sat = [r for r in results if r['date'] == '2025-06-07'][0]
        self.assertIsNone(day_sat['actual_balance'])
        self.assertEqual(day_sat['expected_balance'], 90.0)
        
        day_mon = [r for r in results if r['date'] == '2025-06-09'][0]
        self.assertEqual(day_mon['new_discrepancy'], 0.0)

    def test_floating_point_precision(self):
        # 0.10 + 0.20 should equal 0.30, not 0.30000000000000004
        results = reconcile("data/edge_case_precision_tx.csv", "data/edge_case_precision_bb.csv")
        
        day_2 = [r for r in results if r['date'] == '2025-06-02'][0]
        self.assertEqual(day_2['new_discrepancy'], 0.0)

    def test_out_of_order_and_multiple_same_day(self):
        results = reconcile("data/edge_case_outoforder_tx.csv", "data/edge_case_outoforder_bb.csv")
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]['date'], '2025-06-01')
        self.assertEqual(results[-1]['date'], '2025-06-03')
        
        for row in results:
            self.assertEqual(row['new_discrepancy'], 0.0)

    def test_sample_provided_data_reconciles(self):
        results = reconcile("data/sample_provided_tx.csv", "data/sample_provided_bb.csv")
        self.assertEqual(len(results), 12)
        for row in results:
            if row['actual_balance'] is not None:
                self.assertEqual(row['new_discrepancy'], 0.0,
                    f"Unexpected discrepancy on {row['date']}")

    def test_sample_mismatch_isolates_errors(self):
        # Two deliberate bank errors: $50 gap on 06-03, additional $5 on 06-10
        results = reconcile("data/sample_mismatch_tx.csv", "data/sample_mismatch_bb.csv")

        origin_days = [r for r in results 
                       if r['new_discrepancy'] is not None and r['new_discrepancy'] != 0.0]
        
        self.assertEqual(len(origin_days), 2)
        
        self.assertEqual(origin_days[0]['date'], '2025-06-03')
        self.assertEqual(origin_days[0]['new_discrepancy'], 50.0)
        
        self.assertEqual(origin_days[1]['date'], '2025-06-10')
        self.assertEqual(origin_days[1]['new_discrepancy'], 5.0)
        
        # Everything else should be zero new drift
        carry_days = [r for r in results 
                      if r['new_discrepancy'] is not None and r['new_discrepancy'] == 0.0]
        self.assertEqual(len(carry_days), 10)

if __name__ == '__main__':
    unittest.main()
