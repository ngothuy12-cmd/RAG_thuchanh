import unittest
import json
from hierarchical_rag import parent_retrieve

class TestParentRetrieve(unittest.TestCase):
    def setUp(self):
        self.config = {
            'MULTI_QUERY_COUNT': 3,
            'MULTI_QUERY_ORIGINAL_WEIGHT': 1.5,
            'MULTI_QUERY_VARIANT_WEIGHT': 1.0,
            'MULTI_QUERY_RRF_K': 60,
            'PER_QUERY_CANDIDATES': 5,
            'PARENT_SCORE_CHILD_LIMIT': 2,
            'PARENT_RRF_K': 60,
            'PARENT_CANDIDATES': 10,
            'TOTAL_CONTEXT_MAX_CHARS': 1000
        }
        self.chunks = [{"chunk_id": "test", "source": "s", "page_start": 1, "page_end": 1, "text": "t"}]
        
        self.store = {
            "child_map": {
                "c1": {"child_id": "c1", "parent_id": "p1", "structural_path": {}},
                "c2": {"child_id": "c2", "parent_id": "p1", "structural_path": {}},
                "c3": {"child_id": "c3", "parent_id": "p2", "structural_path": {}},
                "c4": {"child_id": "c4", "parent_id": "p3", "structural_path": {}}
            },
            "parent_map": {
                "p1": {"parent_id": "p1", "source": "s", "page_start": 1, "page_end": 1, "text": "A"*200},
                "p2": {"parent_id": "p2", "source": "s", "page_start": 1, "page_end": 1, "text": "B"*1200}, # oversize
                "p3": {"parent_id": "p3", "source": "s", "page_start": 1, "page_end": 1, "text": "C"*100}
            }
        }
        
    def mock_expand(self, q, conf):
        return {
            "queries": [{"query_id": "Q0", "origin": "original", "text": q}],
            "status": "ready"
        }

    def mock_hybrid(self, text, strategy, chunks):
        # We need mock to return c1, c2, c3, c4
        return {"candidates": [
            {"chunk_id": "c1", "text": "t1", "source": "s", "page_start": 1, "page_end": 1, "fused_rank": 1},
            {"chunk_id": "c2", "text": "t2", "source": "s", "page_start": 1, "page_end": 1, "fused_rank": 2},
            {"chunk_id": "c3", "text": "t3", "source": "s", "page_start": 1, "page_end": 1, "fused_rank": 3},
            {"chunk_id": "c4", "text": "t4", "source": "s", "page_start": 1, "page_end": 1, "fused_rank": 4}
        ]}

    def test_missing_store(self):
        res = parent_retrieve("test", "multi_parent", self.chunks, self.config, hierarchy_store={})
        self.assertEqual(res['status'], "hierarchy_not_ready")

    def test_parent_aggregation_and_cap(self):
        # limit is 2. p1 has c1(mq_rank 1) and c2(mq_rank 2)
        # p2 has c3(mq_rank 3)
        # p3 has c4(mq_rank 4)
        # Note: best child ranks define MQ ranks. 
        res = parent_retrieve("test", "multi_parent", self.chunks, self.config, 
                              self.mock_expand, self.mock_hybrid, self.store)
        
        cands = res['candidates']
        self.assertEqual(cands[0]['parent_id'], 'p1')
        self.assertEqual(len(cands[0]['scoring_child_ids']), 2) # c1, c2
        self.assertEqual(cands[0]['best_child_rank'], 1)
        
        # p1 score: 1/(60+1) + 1/(60+2)
        expected_p1 = 1/61 + 1/62
        self.assertAlmostEqual(cands[0]['parent_rrf_score'], expected_p1)

    def test_oversized_first_parent_budget(self):
        # p2 is oversized (1200 > max 1000). But if it is first, it should be kept with warning.
        # To make p2 first, we can return ONLY c3
        def mock_hybrid_c3_only(text, strategy, chunks):
            return {"candidates": [
                {"chunk_id": "c3", "text": "t3", "source": "s", "page_start": 1, "page_end": 1, "fused_rank": 1},
                {"chunk_id": "c1", "text": "t1", "source": "s", "page_start": 1, "page_end": 1, "fused_rank": 2}
            ]}
            
        res = parent_retrieve("test", "multi_parent", self.chunks, self.config, 
                              self.mock_expand, mock_hybrid_c3_only, self.store)
                              
        cands = res['candidates']
        # p2 (1200) should be first (c3 has rank 1). p1 (200) should be dropped due to budget
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]['parent_id'], 'p2')
        self.assertTrue("first_parent_exceeds_budget" in cands[0]['warnings'])
        self.assertEqual(res['trace']['parent_aggregation']['parents_dropped_by_budget'], 1)

    def test_context_budget_boundary(self):
        # We want p3 (100) then p1 (200) to both fit under budget (1000).
        res = parent_retrieve("test", "multi_parent", self.chunks, self.config, 
                              self.mock_expand, self.mock_hybrid, self.store)
        cands = res['candidates']
        self.assertEqual(len(cands), 2)
        self.assertEqual(cands[0]['parent_id'], 'p1')
        self.assertEqual(cands[1]['parent_id'], 'p3')

if __name__ == '__main__':
    unittest.main()
