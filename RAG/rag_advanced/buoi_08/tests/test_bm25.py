import unittest
from advanced_rag import tokenize_vi_legal, bm25_search

class TestBM25(unittest.TestCase):
    def test_01_tokenizer_keeps_vietnamese(self):
        text = "Lãi suất tài sản bảo đảm."
        tokens = tokenize_vi_legal(text)
        self.assertEqual(tokens, ["lãi", "suất", "tài", "sản", "bảo", "đảm"])
        
    def test_02_tokenizer_keeps_numbers_and_articles(self):
        text = "Điều 7, Khoản 2"
        tokens = tokenize_vi_legal(text)
        self.assertEqual(tokens, ["điều", "7", "khoản", "2"])
        
    def test_03_same_preprocessing(self):
        text = "Cơ cấu lại NỢ"
        q = "cơ cấu LẠI nợ"
        self.assertEqual(tokenize_vi_legal(text), tokenize_vi_legal(q))
        
    def test_04_exact_term_ranking(self):
        chunks = [
            {"chunk_id": "1", "text": "Đoạn văn này không nói về vấn đề đó.", "source": "A", "page_start": 1, "page_end": 1},
            {"chunk_id": "2", "text": "Quy định về tài sản bảo đảm hợp pháp.", "source": "B", "page_start": 2, "page_end": 2},
            {"chunk_id": "3", "text": "Đoạn văn thứ ba không liên quan.", "source": "C", "page_start": 3, "page_end": 3},
        ]
        res = bm25_search("tài sản bảo đảm", chunks, 3)
        self.assertEqual(res[0]["chunk_id"], "2")
        self.assertGreater(res[0]["bm25_score"], res[1]["bm25_score"])
        
    def test_05_candidate_k_larger_than_corpus(self):
        chunks = [
            {"chunk_id": "1", "text": "Luật", "source": "A", "page_start": 1, "page_end": 1}
        ]
        res = bm25_search("Luật", chunks, 100)
        self.assertEqual(len(res), 1)
        
    def test_06_empty_question_fails(self):
        chunks = [{"chunk_id": "1", "text": "A", "source": "A", "page_start": 1, "page_end": 1}]
        with self.assertRaises(ValueError):
            bm25_search("", chunks, 5)
        with self.assertRaises(ValueError):
            bm25_search("   ", chunks, 5)
        with self.assertRaises(ValueError):
            bm25_search(",.,.", chunks, 5)
            
    def test_07_tie_break_deterministic(self):
        chunks = [
            {"chunk_id": "B_id", "text": "Một văn bản chung", "source": "A", "page_start": 1, "page_end": 1},
            {"chunk_id": "A_id", "text": "Một văn bản chung", "source": "A", "page_start": 1, "page_end": 1},
        ]
        # B_id and A_id will have the same score, sorted by chunk_id
        res = bm25_search("văn bản", chunks, 2)
        self.assertEqual(res[0]["chunk_id"], "A_id")
        self.assertEqual(res[1]["chunk_id"], "B_id")

if __name__ == '__main__':
    unittest.main()
