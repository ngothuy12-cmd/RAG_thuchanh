import unittest
import math
from unittest.mock import patch, MagicMock
from advanced_rag import rerank_candidates

class TestReranker(unittest.TestCase):
    def setUp(self):
        self.hybrid_candidates = [
            {"chunk_id": f"chunk_{i}", "text": f"text {i}", "fused_rank": i} 
            for i in range(1, 11)
        ]
        
    @patch('advanced_rag.load_config')
    @patch('advanced_rag.get_reranker')
    def test_lazy_loading_and_limit(self, mock_get_reranker, mock_config):
        mock_config.return_value = {
            'RERANK_CANDIDATES': 3,
            'FINAL_TOP_K': 2,
            'RERANKER_MAX_LENGTH': 512,
            'RERANK_BATCH_SIZE': 2,
            'RERANKER_MODEL': 'fake-model'
        }
        
        # Test 1: Lazy loading - if fake_reranker is provided, get_reranker should NOT be called.
        # Test 7: Limit - Only 3 candidates should be passed to the reranker.
        def fake_rerank(q, texts):
            self.assertEqual(len(texts), 3) # only top 3 passed
            return [2.0, -1.0, 0.0]
            
        result = rerank_candidates("query", self.hybrid_candidates, fake_reranker=fake_rerank)
        
        mock_get_reranker.assert_not_called()
        
        # Test 8: Only final_k returned
        candidates = result['candidates']
        self.assertEqual(len(candidates), 2)
        
        # Test 4: Sigmoid correct
        # chunk_1 got 2.0 -> sigmoid(2.0)
        c1 = next(c for c in candidates if c['chunk_id'] == 'chunk_1')
        self.assertAlmostEqual(c1['rerank_score'], 1.0 / (1.0 + math.exp(-2.0)))
        
        # chunk_3 got 0.0 -> sigmoid(0.0) = 0.5
        c3 = next(c for c in candidates if c['chunk_id'] == 'chunk_3')
        self.assertAlmostEqual(c3['rerank_score'], 0.5)
        
        # chunk_2 got -1.0, should be dropped because we only keep 2 out of 3.
        with self.assertRaises(StopIteration):
            next(c for c in candidates if c['chunk_id'] == 'chunk_2')

    @patch('advanced_rag.load_config')
    def test_sort_and_tie_break(self, mock_config):
        mock_config.return_value = {
            'RERANK_CANDIDATES': 10,
            'FINAL_TOP_K': 5,
            'RERANKER_MAX_LENGTH': 512,
            'RERANK_BATCH_SIZE': 2,
            'RERANKER_MODEL': 'fake-model'
        }
        
        def fake_rerank(q, texts):
            # All get same score 0.0 except first one gets 1.0
            return [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            
        # fused_rank is 1 to 10
        result = rerank_candidates("query", self.hybrid_candidates, fake_reranker=fake_rerank)
        candidates = result['candidates']
        
        # First is chunk_1 because of score 1.0
        self.assertEqual(candidates[0]['chunk_id'], 'chunk_1')
        # The rest have same score, so tie-break falls back to fused_rank asc, which means chunk_2, chunk_3, etc.
        self.assertEqual(candidates[1]['chunk_id'], 'chunk_2')
        self.assertEqual(candidates[2]['chunk_id'], 'chunk_3')

    @patch('advanced_rag.load_config')
    def test_rank_change(self, mock_config):
        mock_config.return_value = {
            'RERANK_CANDIDATES': 5,
            'FINAL_TOP_K': 5,
            'RERANKER_MAX_LENGTH': 512,
            'RERANK_BATCH_SIZE': 2,
            'RERANKER_MODEL': 'fake-model'
        }
        
        # chunk_5 gets highest score, should move to rank 1
        # It was fused_rank 5. rank_change should be 5 - 1 = +4
        def fake_rerank(q, texts):
            return [0.1, 0.2, 0.3, 0.4, 10.0]
            
        result = rerank_candidates("query", self.hybrid_candidates, fake_reranker=fake_rerank)
        c5 = result['candidates'][0]
        self.assertEqual(c5['chunk_id'], 'chunk_5')
        self.assertEqual(c5['rerank_rank'], 1)
        self.assertEqual(c5['rank_change'], 4)
        
    @patch('advanced_rag.load_config')
    @patch('advanced_rag.get_reranker')
    def test_model_error_no_fallback(self, mock_get, mock_config):
        mock_config.return_value = {
            'RERANK_CANDIDATES': 5,
            'FINAL_TOP_K': 5,
            'RERANKER_MAX_LENGTH': 512,
            'RERANK_BATCH_SIZE': 2,
            'RERANKER_MODEL': 'fake-model'
        }
        
        mock_get.side_effect = RuntimeError("reranker_unavailable: Lỗi")
        
        with self.assertRaisesRegex(RuntimeError, "reranker_unavailable"):
            rerank_candidates("q", self.hybrid_candidates)

if __name__ == '__main__':
    unittest.main()
