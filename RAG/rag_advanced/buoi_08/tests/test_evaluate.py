import unittest
import math
from evaluate import dcg_at_k, ndcg_at_k, recall_at_k, mrr_at_k

class TestEvaluateMetrics(unittest.TestCase):
    def test_dcg_at_k(self):
        # r[0]/log2(2) + r[1]/log2(3) -> 1 + 1/1.58 = 1.63
        r = [1, 1, 0]
        self.assertAlmostEqual(dcg_at_k(r, 3), 1.0 + 1.0/math.log2(3))
        
        r2 = [0, 1, 0]
        self.assertAlmostEqual(dcg_at_k(r2, 3), 1.0/math.log2(3))

    def test_ndcg_at_k(self):
        r = [0, 1, 0]
        ideal = [1, 0, 0]  # only 1 relevant
        
        ideal_dcg = dcg_at_k(ideal, 3)
        actual_dcg = dcg_at_k(r, 3)
        self.assertAlmostEqual(ndcg_at_k(r, 3), actual_dcg / ideal_dcg)

    def test_recall_at_k(self):
        r = [1, 0, 1]
        self.assertEqual(recall_at_k(r, 3, 2), 1.0)
        self.assertEqual(recall_at_k(r, 2, 2), 0.5)
        self.assertEqual(recall_at_k(r, 3, 0), 0.0) # avoid division by zero

    def test_mrr_at_k(self):
        self.assertEqual(mrr_at_k([0, 1, 0], 3), 0.5)
        self.assertEqual(mrr_at_k([0, 0, 1], 3), 1/3)
        self.assertEqual(mrr_at_k([1, 0, 0], 3), 1.0)
        self.assertEqual(mrr_at_k([0, 0, 0], 3), 0.0)

if __name__ == '__main__':
    unittest.main()
