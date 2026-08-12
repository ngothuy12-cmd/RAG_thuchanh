import unittest
import json
from hierarchical_rag import expand_query, _QUERY_CACHE, normalize_text

class TestQueryExpansion(unittest.TestCase):
    def setUp(self):
        _QUERY_CACHE.clear()
        self.config = {
            'MULTI_QUERY_COUNT': 3,
            'MULTI_QUERY_MAX_CHARS': 300,
            'MULTI_QUERY_TEMPERATURE': 0.2,
            'GEMINI_GENERATION_MODEL': 'mock-model'
        }

    def mock_generator(self, prompt):
        return [
            {"text": "  điều kiện vay vốn  ", "focus": "paraphrase"},
            {"text": "điều kiện vay vốn", "focus": "duplicate"}, # should be dropped
            {"text": "Quy định tại điều 5 về vay vốn", "focus": "hallucinated ref"}, # hallucinated article 5
            {"text": "nhu cầu vốn không được cho vay", "focus": "missing aspect"}
        ]

    def test_q0_preservation_and_trim(self):
        q = "   Hỏi về vay vốn   "
        res = expand_query(q, self.config, query_generator_fn=lambda p: [])
        self.assertEqual(res['original_question'], "Hỏi về vay vốn")
        self.assertEqual(len(res['queries']), 1)
        self.assertEqual(res['queries'][0]['query_id'], "Q0")
        self.assertEqual(res['queries'][0]['text'], "Hỏi về vay vốn")

    def test_schema_and_duplicate_drop(self):
        q = "điều kiện vay vốn"
        res = expand_query(q, self.config, query_generator_fn=self.mock_generator)
        
        # Q0: "điều kiện vay vốn"
        # gen 1: "điều kiện vay vốn" -> dropped (duplicate with Q0)
        # gen 2: "điều kiện vay vốn" -> dropped (duplicate)
        # gen 3: "Quy định tại điều 5 về vay vốn" -> dropped (hallucinates điều 5)
        # gen 4: "nhu cầu vốn không được cho vay" -> kept
        
        self.assertEqual(len(res['queries']), 2)
        self.assertEqual(res['queries'][0]['query_id'], "Q0")
        self.assertEqual(res['queries'][1]['query_id'], "Q1")
        self.assertEqual(res['queries'][1]['text'], "nhu cầu vốn không được cho vay")
        self.assertEqual(res['dropped_duplicate_count'], 2)

    def test_legal_reference_hallucination_prevention(self):
        # Q0 does not have 'điều'
        q = "Quy định vay vốn"
        def mock_gen(p):
            return [{"text": "Theo điều 20 quy định vay vốn thế nào?", "focus": "x"}]
        res = expand_query(q, self.config, query_generator_fn=mock_gen)
        # Should drop the generated one
        self.assertEqual(len(res['queries']), 1)

    def test_cache_hit(self):
        q = "Test cache"
        def mock_gen(p): return [{"text": "cached variant", "focus": "x"}]
        
        res1 = expand_query(q, self.config, query_generator_fn=mock_gen)
        self.assertFalse(res1['cache_hit'])
        self.assertEqual(len(res1['queries']), 2)
        
        # Call again without generator function, should hit cache
        def mock_gen_fail(p): raise Exception("Should not be called")
        res2 = expand_query(q, self.config, query_generator_fn=mock_gen_fail)
        self.assertTrue(res2['cache_hit'])
        self.assertEqual(res2['queries'], res1['queries'])

    def test_api_failure(self):
        q = "Fail test"
        def mock_gen_fail(p): raise Exception("API Error")
        res = expand_query(q, self.config, query_generator_fn=mock_gen_fail)
        self.assertEqual(res['status'], "query_generation_unavailable")
        self.assertEqual(len(res['queries']), 1) # Fallback to Q0

if __name__ == '__main__':
    unittest.main()
