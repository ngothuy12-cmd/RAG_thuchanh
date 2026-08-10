import unittest
from unittest.mock import patch, MagicMock
from advanced_rag import query_pipeline

class TestQueryPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_config = {
            'FINAL_TOP_K': 2,
            'RAG_MAX_DISTANCE': 0.45,
            'RERANK_MIN_SCORE': 0.5
        }
        
        self.mock_candidates = [
            {
                "chunk_id": "c1", "text": "Text 1", "source": "A.pdf", "page_start": 1, "page_end": 1,
                "semantic_distance": 0.4, "rerank_score": 0.9, "fused_rank": 1
            },
            {
                "chunk_id": "c2", "text": "Text 2", "source": "B.pdf", "page_start": 2, "page_end": 2,
                "semantic_distance": 0.5, "rerank_score": 0.4, "fused_rank": 2
            }
        ]

    def _get_mock_res(self):
        return {
            'candidates': self.mock_candidates,
            'trace': {
                'latency_ms': {'tokenize_bm25': 1, 'semantic': 2, 'fusion': 3},
                'bm25_candidate_count': 5,
                'semantic_candidate_count': 5,
                'overlap_count': 2,
                'union_count': 8
            }
        }

    @patch('advanced_rag.load_config')
    @patch('advanced_rag.load_chunks')
    @patch('advanced_rag.hybrid_search')
    @patch('advanced_rag.rerank_candidates')
    def test_gating_and_prompt(self, mock_rerank, mock_hybrid, mock_load, mock_config):
        mock_config.return_value = self.mock_config
        mock_load.return_value = ([], {})
        mock_hybrid.return_value = self._get_mock_res()
        mock_rerank.return_value = {
            'candidates': self.mock_candidates,
            'trace': {'rerank_latency_ms': 10, 'rerank_candidates_count': 2}
        }
        
        called_prompts = []
        def fake_gen(prompt):
            called_prompts.append(prompt)
            return "Theo [E1], đây là test."
            
        res = query_pipeline("Q?", "hierarchical", "hybrid_rerank", fake_gen=fake_gen)
        
        # Gating: c1 rerank_score 0.9 >= 0.5 (Accepted). c2 rerank_score 0.4 < 0.5 (Rejected).
        self.assertEqual(res['trace']['accepted'], 1)
        self.assertEqual(res['evidence'][0]['accepted'], True)
        self.assertEqual(res['evidence'][1]['accepted'], False)
        
        # Generation: Should only have E1 in prompt, not E2.
        self.assertEqual(len(called_prompts), 1)
        self.assertIn("[E1]", called_prompts[0])
        self.assertIn("Text 1", called_prompts[0])
        self.assertNotIn("[E2]", called_prompts[0])
        self.assertNotIn("Text 2", called_prompts[0])
        
        # Citation map
        self.assertEqual(len(res['citations']), 1)
        self.assertEqual(res['citations'][0]['chunk_id'], 'c1')
        self.assertEqual(res['status'], 'answered')
        
        # Schema trace
        self.assertIn("bm25_candidates", res['trace'])
        self.assertIn("rerank", res['trace']['latency_ms'])

    @patch('advanced_rag.load_config')
    @patch('advanced_rag.load_chunks')
    @patch('advanced_rag.hybrid_search')
    @patch('advanced_rag.rerank_candidates')
    def test_compare_no_gen(self, mock_rerank, mock_hybrid, mock_load, mock_config):
        mock_config.return_value = self.mock_config
        mock_load.return_value = ([], {})
        mock_hybrid.return_value = self._get_mock_res()
        mock_rerank.return_value = {
            'candidates': self.mock_candidates,
            'trace': {'rerank_latency_ms': 10, 'rerank_candidates_count': 2}
        }
        
        # If generation returns "", status should be retrieval_only
        res = query_pipeline("Q?", "hierarchical", "hybrid_rerank", fake_gen=lambda x: "")
        self.assertEqual(res['status'], 'retrieval_only')
        self.assertEqual(len(res['evidence']), 2)
        
    @patch('advanced_rag.load_config')
    @patch('advanced_rag.load_chunks')
    @patch('advanced_rag.hybrid_search')
    @patch('advanced_rag.rerank_candidates')
    def test_reranker_unavailable(self, mock_rerank, mock_hybrid, mock_load, mock_config):
        mock_config.return_value = self.mock_config
        mock_load.return_value = ([], {})
        mock_hybrid.return_value = self._get_mock_res()
        mock_rerank.side_effect = RuntimeError("reranker_unavailable: Lỗi fake")
        
        res = query_pipeline("Q?", "hierarchical", "hybrid_rerank")
        self.assertEqual(res['status'], 'reranker_unavailable')
        self.assertIn('reranker_unavailable', res['warnings'][0])
        # Should still have evidence from hybrid
        self.assertEqual(len(res['evidence']), 2)

    @patch('advanced_rag.load_config')
    @patch('advanced_rag.load_chunks')
    @patch('advanced_rag.hybrid_search')
    def test_diagnostic_gating(self, mock_hybrid, mock_load, mock_config):
        mock_config.return_value = self.mock_config
        mock_load.return_value = ([], {})
        mock_hybrid.return_value = self._get_mock_res()
        
        # Mode hybrid (diagnostic). 
        # c1 has semantic_distance 0.4 <= 0.45. So BOTH should be accepted because has_semantic_match = True
        res = query_pipeline("Q?", "hierarchical", "hybrid", fake_gen=lambda x: "")
        self.assertEqual(res['trace']['accepted'], 2)
        
        # Change c1 semantic distance to fail
        self.mock_candidates[0]['semantic_distance'] = 0.5
        res = query_pipeline("Q?", "hierarchical", "hybrid", fake_gen=lambda x: "")
        # has_semantic_match = False, so 0 accepted.
        self.assertEqual(res['trace']['accepted'], 0)
        self.assertEqual(res['status'], 'insufficient_evidence')
        self.assertFalse(res['trace']['generation_called'])

if __name__ == '__main__':
    unittest.main()
