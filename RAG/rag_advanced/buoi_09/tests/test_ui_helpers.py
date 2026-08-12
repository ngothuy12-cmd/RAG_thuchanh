import unittest
from ui_helpers import (
    format_citation, build_query_child_matrix, build_parent_tree_data,
    map_status_to_warning, build_compare_row
)

class TestUIHelpers(unittest.TestCase):
    def test_citation_formatting(self):
        cite = {
            "evidence_id": "P1", "source": "test.pdf", 
            "page_start": 1, "page_end": 2, "parent_rerank_score": 0.881
        }
        res = format_citation(cite)
        self.assertIn("[P1]", res)
        self.assertIn("test.pdf", res)
        self.assertIn("p.1-2", res)
        self.assertIn("0.88", res)
        
    def test_query_child_matrix(self):
        queries = [{"query_id": "Q0"}, {"query_id": "Q1"}]
        cands = [{
            "child_id": "c1", "support_query_ids": ["Q0", "Q1"],
            "multi_query_rrf_score": 0.5, "per_query_ranks": {"Q0": 1, "Q1": 2}
        }]
        
        mat = build_query_child_matrix(queries, cands)
        self.assertEqual(len(mat), 1)
        self.assertEqual(mat[0]["Q0"], 1)
        self.assertEqual(mat[0]["Q1"], 2)
        
    def test_parent_tree_data(self):
        cands = [{
            "parent_id": "p1", "source": "s", "page_start": 1, "page_end": 1,
            "parent_rank": 1, "parent_rerank_rank": 1, "parent_rrf_score": 0.5, "parent_rerank_score": 0.9,
            "anchor_child_id": "c1",
            "_hits": [{"child_id": "c1", "support_query_ids": ["Q0"], "text": "abc"}]
        }]
        
        tree = build_parent_tree_data(cands)
        self.assertEqual(tree[0]['parent_id'], 'p1')
        self.assertEqual(len(tree[0]['supporting_children']), 1)
        self.assertTrue(tree[0]['supporting_children'][0]['anchor'])
        
    def test_map_warning(self):
        level, msg = map_status_to_warning("hierarchy_not_ready")
        self.assertEqual(level, "error")
        self.assertIn("Hierarchy chưa sẵn sàng", msg)
        
    def test_compare_row(self):
        res = {
            "status": "success",
            "accepted_evidence": [{"parent_id": "p1", "source": "s"}],
            "trace": {"api_calls": {"generation": 1}, "parent_aggregation": {"expansion_factor": 2.5}}
        }
        row = build_compare_row("multi_parent", res)
        self.assertEqual(row["Mode"], "multi_parent")
        self.assertEqual(row["Expansion Factor"], "2.50x")
        self.assertEqual(row["Gen Calls"], 1)

if __name__ == '__main__':
    unittest.main()
