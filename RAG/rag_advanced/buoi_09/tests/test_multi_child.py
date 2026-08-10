import unittest
import json
from hierarchical_rag import multi_query_child_search

class TestMultiQueryChildSearch(unittest.TestCase):
    def setUp(self):
        self.config = {
            'MULTI_QUERY_COUNT': 3,
            'MULTI_QUERY_ORIGINAL_WEIGHT': 1.5,
            'MULTI_QUERY_VARIANT_WEIGHT': 1.0,
            'MULTI_QUERY_RRF_K': 60,
            'PER_QUERY_CANDIDATES': 5,
        }
        self.chunks = [{"chunk_id": "test", "source": "s", "page_start": 1, "page_end": 1, "text": "t"}]
        
    def mock_expand(self, q, conf):
        return {
            "queries": [
                {"query_id": "Q0", "origin": "original", "text": "Q0 text"},
                {"query_id": "Q1", "origin": "generated", "text": "Q1 text"},
                {"query_id": "Q2", "origin": "generated", "text": "Q2 text"}
            ],
            "status": "ready"
        }

    def test_rrf_calculation_and_merge(self):
        def mock_hybrid(text, strategy, chunks):
            # Return different results based on text
            if "Q0" in text:
                return {"candidates": [
                    {"chunk_id": "c1", "text": "t1", "source": "s1", "page_start": 1, "page_end": 1, "fused_rank": 1},
                    {"chunk_id": "c2", "text": "t2", "source": "s1", "page_start": 1, "page_end": 1, "fused_rank": 2}
                ]}
            elif "Q1" in text:
                return {"candidates": [
                    {"chunk_id": "c1", "text": "t1", "source": "s1", "page_start": 1, "page_end": 1, "fused_rank": 2},
                    {"chunk_id": "c3", "text": "t3", "source": "s1", "page_start": 1, "page_end": 1, "fused_rank": 1}
                ]}
            else:
                return {"candidates": []}

        res = multi_query_child_search("test", "hierarchical", self.chunks, self.config, 
                                       expand_fn=self.mock_expand, hybrid_fn=mock_hybrid)
        
        cands = res['candidates']
        self.assertEqual(len(cands), 3) # c1, c2, c3
        
        c1 = next(c for c in cands if c['child_id'] == 'c1')
        c2 = next(c for c in cands if c['child_id'] == 'c2')
        c3 = next(c for c in cands if c['child_id'] == 'c3')
        
        # c1 rrf: Q0(rank 1, w 1.5) + Q1(rank 2, w 1.0) = 1.5/(60+1) + 1.0/(60+2)
        expected_c1 = 1.5/61 + 1.0/62
        self.assertAlmostEqual(c1['multi_query_rrf_score'], expected_c1)
        
        # c2 rrf: Q0(rank 2, w 1.5) = 1.5/62
        expected_c2 = 1.5/62
        self.assertAlmostEqual(c2['multi_query_rrf_score'], expected_c2)
        
        # c3 rrf: Q1(rank 1, w 1.0) = 1.0/61
        expected_c3 = 1.0/61
        self.assertAlmostEqual(c3['multi_query_rrf_score'], expected_c3)
        
        self.assertEqual(c1['support_query_count'], 2)
        self.assertEqual(c2['support_query_count'], 1)
        self.assertEqual(c1['support_query_ids'], ['Q0', 'Q1'])
        self.assertEqual(c2['support_query_ids'], ['Q0'])
        
        # Check sort order: c1 > c2 > c3
        self.assertEqual(cands[0]['child_id'], 'c1')
        self.assertEqual(cands[1]['child_id'], 'c2')
        self.assertEqual(cands[2]['child_id'], 'c3')

    def test_metadata_mismatch_fails(self):
        def mock_hybrid(text, strategy, chunks):
            if "Q0" in text:
                return {"candidates": [
                    {"chunk_id": "c1", "text": "t1", "source": "s1", "page_start": 1, "page_end": 1, "fused_rank": 1}
                ]}
            else:
                return {"candidates": [
                    {"chunk_id": "c1", "text": "DIFFERENT", "source": "s1", "page_start": 1, "page_end": 1, "fused_rank": 1}
                ]}

        with self.assertRaisesRegex(ValueError, "Metadata mismatch"):
            multi_query_child_search("test", "hierarchical", self.chunks, self.config, 
                                     expand_fn=self.mock_expand, hybrid_fn=mock_hybrid)

    def test_q0_failure(self):
        def mock_hybrid(text, strategy, chunks):
            if "Q0" in text:
                raise Exception("Q0 error")
            return {"candidates": []}
            
        res = multi_query_child_search("test", "hierarchical", self.chunks, self.config, 
                                       expand_fn=self.mock_expand, hybrid_fn=mock_hybrid)
        
        self.assertEqual(res['status'], "multi_query_failed")
        self.assertTrue("Q0 retrieval failed" in res['error'])

    def test_generated_query_failure_partial(self):
        def mock_hybrid(text, strategy, chunks):
            if "Q1" in text:
                raise Exception("Q1 error")
            return {"candidates": [
                {"chunk_id": "c1", "text": "t1", "source": "s1", "page_start": 1, "page_end": 1, "fused_rank": 1}
            ]}
            
        res = multi_query_child_search("test", "hierarchical", self.chunks, self.config, 
                                       expand_fn=self.mock_expand, hybrid_fn=mock_hybrid)
        
        self.assertEqual(res['status'], "multi_query_partial")
        self.assertEqual(len(res['candidates']), 1)
        self.assertEqual(res['trace']['queries_failed'], 1)
        self.assertTrue(any("Q1 failed" in w for w in res['warnings']))

if __name__ == '__main__':
    unittest.main()
