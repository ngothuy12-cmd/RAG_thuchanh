import unittest
from unittest.mock import patch, MagicMock
from advanced_rag import hybrid_search

class TestHybrid(unittest.TestCase):
    def setUp(self):
        self.chunks = [{"chunk_id": f"chunk_{i}", "text": f"text {i}", "source": "A", "page_start": 1, "page_end": 1} for i in range(1, 6)]
        
    @patch('advanced_rag.semantic_search')
    @patch('advanced_rag.bm25_search')
    @patch('advanced_rag.load_config')
    def test_01_rrf_formula_and_overlap(self, mock_config, mock_bm25, mock_semantic):
        mock_config.return_value = {
            'RRF_K': 60,
            'RRF_BM25_WEIGHT': 1.0,
            'RRF_SEMANTIC_WEIGHT': 1.0,
            'BM25_CANDIDATES': 20,
            'SEMANTIC_CANDIDATES': 20
        }
        
        mock_bm25.return_value = [
            {"chunk_id": "chunk_1", "text": "text 1", "source": "A", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0},
            {"chunk_id": "chunk_2", "text": "text 2", "source": "A", "page_start": 1, "page_end": 1, "bm25_rank": 2, "bm25_score": 5.0}
        ]
        
        mock_semantic.return_value = [
            {"chunk_id": "chunk_3", "text": "text 3", "source": "A", "page_start": 1, "page_end": 1, "semantic_rank": 1, "semantic_distance": 0.1},
            {"chunk_id": "chunk_1", "text": "text 1", "source": "A", "page_start": 1, "page_end": 1, "semantic_rank": 2, "semantic_distance": 0.2}
        ]
        
        result = hybrid_search("q", "hierarchical", self.chunks)
        candidates = result['candidates']
        trace = result['trace']
        
        # Test 2, 3, 4: Counts
        self.assertEqual(len(candidates), 3) 
        self.assertEqual(trace['union_count'], 3)
        self.assertEqual(trace['overlap_count'], 1)
        self.assertEqual(trace['bm25_candidate_count'], 2)
        self.assertEqual(trace['semantic_candidate_count'], 2)
        
        # Test 1: RRF formula
        c1 = next(c for c in candidates if c['chunk_id'] == 'chunk_1')
        c2 = next(c for c in candidates if c['chunk_id'] == 'chunk_2')
        c3 = next(c for c in candidates if c['chunk_id'] == 'chunk_3')
        
        expected_c1 = 1.0/61.0 + 1.0/62.0
        self.assertAlmostEqual(c1['rrf_score'], expected_c1)
        self.assertEqual(len(c1['matched_by']), 2)
        
        self.assertAlmostEqual(c2['rrf_score'], 1.0/62.0)
        self.assertEqual(c2['matched_by'], ['bm25'])
        
        self.assertAlmostEqual(c3['rrf_score'], 1.0/61.0)
        self.assertEqual(c3['matched_by'], ['semantic'])
        
        # Test 9: Called once
        mock_bm25.assert_called_once()
        mock_semantic.assert_called_once()
        
    @patch('advanced_rag.semantic_search')
    @patch('advanced_rag.bm25_search')
    @patch('advanced_rag.load_config')
    def test_05_weights_zero(self, mock_config, mock_bm25, mock_semantic):
        mock_config.return_value = {
            'RRF_K': 60,
            'RRF_BM25_WEIGHT': 0.0,
            'RRF_SEMANTIC_WEIGHT': 1.0,
            'BM25_CANDIDATES': 20,
            'SEMANTIC_CANDIDATES': 20
        }
        
        mock_semantic.return_value = [
            {"chunk_id": "chunk_3", "text": "text 3", "source": "A", "page_start": 1, "page_end": 1, "semantic_rank": 1, "semantic_distance": 0.1},
        ]
        
        result = hybrid_search("q", "hierarchical", self.chunks)
        mock_bm25.assert_not_called()
        self.assertEqual(len(result['candidates']), 1)

    @patch('advanced_rag.semantic_search')
    @patch('advanced_rag.bm25_search')
    @patch('advanced_rag.load_config')
    def test_06_tie_break(self, mock_config, mock_bm25, mock_semantic):
        mock_config.return_value = {
            'RRF_K': 60,
            'RRF_BM25_WEIGHT': 1.0,
            'RRF_SEMANTIC_WEIGHT': 1.0,
            'BM25_CANDIDATES': 20,
            'SEMANTIC_CANDIDATES': 20
        }
        
        mock_bm25.return_value = [
            {"chunk_id": "chunk_B", "text": "text B", "source": "B", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0},
        ]
        mock_semantic.return_value = [
            {"chunk_id": "chunk_A", "text": "text A", "source": "A", "page_start": 1, "page_end": 1, "semantic_rank": 1, "semantic_distance": 0.1},
        ]
        
        result = hybrid_search("q", "hierarchical", self.chunks)
        self.assertEqual(result['candidates'][0]['chunk_id'], 'chunk_A')
        self.assertEqual(result['candidates'][1]['chunk_id'], 'chunk_B')
        
    @patch('advanced_rag.semantic_search')
    @patch('advanced_rag.bm25_search')
    @patch('advanced_rag.load_config')
    def test_07_metadata_mismatch(self, mock_config, mock_bm25, mock_semantic):
        mock_config.return_value = {
            'RRF_K': 60,
            'RRF_BM25_WEIGHT': 1.0,
            'RRF_SEMANTIC_WEIGHT': 1.0,
            'BM25_CANDIDATES': 20,
            'SEMANTIC_CANDIDATES': 20
        }
        
        mock_bm25.return_value = [
            {"chunk_id": "chunk_1", "text": "text 1", "source": "A", "page_start": 1, "page_end": 1, "bm25_rank": 1, "bm25_score": 10.0}
        ]
        mock_semantic.return_value = [
            {"chunk_id": "chunk_1", "text": "text WRONG", "source": "A", "page_start": 1, "page_end": 1, "semantic_rank": 1, "semantic_distance": 0.1}
        ]
        
        with self.assertRaises(ValueError) as e:
            hybrid_search("q", "hierarchical", self.chunks)
        self.assertIn("Metadata mismatch", str(e.exception))

if __name__ == '__main__':
    unittest.main()
