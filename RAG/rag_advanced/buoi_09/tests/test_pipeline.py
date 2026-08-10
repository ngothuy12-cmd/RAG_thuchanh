import unittest
from hierarchical_rag import execute_pipeline

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.config = {
            'MULTI_QUERY_COUNT': 2,
            'MULTI_QUERY_ORIGINAL_WEIGHT': 1.5,
            'MULTI_QUERY_VARIANT_WEIGHT': 1.0,
            'MULTI_QUERY_RRF_K': 60,
            'PER_QUERY_CANDIDATES': 5,
            'PARENT_SCORE_CHILD_LIMIT': 2,
            'PARENT_RRF_K': 60,
            'PARENT_CANDIDATES': 5,
            'TOTAL_CONTEXT_MAX_CHARS': 5000,
            'FINAL_PARENT_TOP_K': 2,
            'RERANK_MIN_SCORE': 0.5
        }
        self.chunks = [{"chunk_id": "c1", "source": "s", "page_start": 1, "page_end": 1, "text": "t"}]
        self.store = {
            "child_map": {"c1": {"child_id": "c1", "parent_id": "p1", "structural_path": {}}},
            "parent_map": {"p1": {"parent_id": "p1", "source": "s", "page_start": 1, "page_end": 1, "text": "A"}}
        }
        
    def mock_expand(self, q, conf):
        return {"queries": [{"query_id": "Q0", "origin": "original", "text": q}], "status": "ready"}
        
    def mock_hybrid(self, text, strategy, chunks):
        return {"candidates": [
            {"chunk_id": "c1", "text": "t", "source": "s", "page_start": 1, "page_end": 1, "fused_rank": 1}
        ]}
        
    def mock_rerank(self, q, texts):
        return [2.0] # High score -> Sigmoid ~ 0.88 > 0.5
        
    def mock_gen(self, prompt):
        return "The answer [P1]"

    def test_single_flat_routing(self):
        res = execute_pipeline("test", "single_flat", self.chunks, self.config,
                               expand_fn=self.mock_expand, hybrid_fn=self.mock_hybrid,
                               rerank_fn=self.mock_rerank, generation_fn=self.mock_gen)
        
        self.assertEqual(res['status'], "success")
        self.assertEqual(res['mode'], "single_flat")
        self.assertTrue(any(c['parent_id'] == 'c1' for c in res['parent_candidates'])) # Fake parent ID for flat

    def test_multi_parent_success(self):
        res = execute_pipeline("test", "multi_parent", self.chunks, self.config,
                               expand_fn=self.mock_expand, hybrid_fn=self.mock_hybrid,
                               rerank_fn=self.mock_rerank, generation_fn=self.mock_gen,
                               hierarchy_store=self.store)
                               
        self.assertEqual(res['status'], "success")
        self.assertEqual(res['mode'], "multi_parent")
        self.assertEqual(len(res['accepted_evidence']), 1)
        self.assertEqual(res['answer'], "The answer [P1]")

    def test_insufficient_evidence_gate(self):
        # mock rerank with low score
        def mock_low_rerank(q, texts): return [-2.0] # sigmoid ~ 0.11 < 0.5
        
        res = execute_pipeline("test", "multi_parent", self.chunks, self.config,
                               expand_fn=self.mock_expand, hybrid_fn=self.mock_hybrid,
                               rerank_fn=mock_low_rerank, generation_fn=self.mock_gen,
                               hierarchy_store=self.store)
                               
        self.assertEqual(res['status'], "insufficient_evidence")

    def test_skip_generation(self):
        res = execute_pipeline("test", "multi_parent", self.chunks, self.config,
                               expand_fn=self.mock_expand, hybrid_fn=self.mock_hybrid,
                               rerank_fn=self.mock_rerank, generation_fn=self.mock_gen,
                               hierarchy_store=self.store, skip_generation=True)
                               
        self.assertTrue('answer' not in res)

if __name__ == '__main__':
    unittest.main()
