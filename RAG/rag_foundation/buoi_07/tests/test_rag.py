import unittest
from unittest.mock import patch, MagicMock
import tempfile
import pathlib
import json
import os
import math
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import rag

MOCK_CONFIG = {
    'GEMINI_API_KEY': 'fake_key',
    'GEMINI_EMBEDDING_MODEL': 'fake-embed',
    'GEMINI_EMBEDDING_DIM': 128,
    'GEMINI_GENERATION_MODEL': 'fake-gen',
    'DEFAULT_TOP_K': 5,
    'RAG_MAX_DISTANCE': 0.5
}

class MockEmbedResponse:
    def __init__(self, values):
        self.embeddings = [type('obj', (object,), {'values': values})]

class MockGenerateResponse:
    def __init__(self, text):
        self.text = text

class MockGenAIClient:
    embed_call_count = 0
    generate_call_count = 0
    embed_fail_mode = None
    gen_text = "Đây là câu trả lời [E1]"
    gen_fail = False
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.models = self
        
    def embed_content(self, model, contents, config):
        MockGenAIClient.embed_call_count += 1
        dim = config.output_dimensionality or 128
        val = 0.1
        if "query:" in contents:
            val = 0.2
        vec = [val] * dim
        
        if MockGenAIClient.embed_fail_mode == 'wrong_dim': vec = [0.1]*(dim-1)
        elif MockGenAIClient.embed_fail_mode == 'nan': vec[0] = math.nan
        elif MockGenAIClient.embed_fail_mode == 'empty': vec = []
        elif MockGenAIClient.embed_fail_mode == 'boolean': vec = [True]*dim
        elif MockGenAIClient.embed_fail_mode == 'zero': vec = [0.0]*dim
        return MockEmbedResponse(vec)
        
    def generate_content(self, model, contents, config):
        MockGenAIClient.generate_call_count += 1
        if MockGenAIClient.gen_fail:
            raise Exception("Mock generation error")
        return MockGenerateResponse(MockGenAIClient.gen_text)


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = pathlib.Path(self.temp_dir.name)
        
        self.patcher_config = patch('rag.load_config', return_value=MOCK_CONFIG.copy())
        self.patcher_config.start()
        
        self.patcher_genai = patch('rag.genai.Client', MockGenAIClient)
        self.patcher_genai.start()
        MockGenAIClient.embed_call_count = 0
        MockGenAIClient.generate_call_count = 0
        MockGenAIClient.embed_fail_mode = None
        MockGenAIClient.gen_fail = False
        MockGenAIClient.gen_text = "Câu trả lời [E1]"
        
        import chromadb
        self.chroma_client = chromadb.PersistentClient(path=str(self.temp_path / "chroma"))
        self.patcher_chroma = patch('rag.get_chroma_client', return_value=self.chroma_client)
        self.patcher_chroma.start()
        
    def tearDown(self):
        self.patcher_config.stop()
        self.patcher_genai.stop()
        self.patcher_chroma.stop()
        self.temp_dir.cleanup()
        
    def create_chunks_file(self, data, filename="test.json"):
        p = self.temp_path / filename
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return self.temp_path


class TestLoader(BaseTest):
    def test_01_read_json_list(self):
        d = self.create_chunks_file([{"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "A"}])
        c, _ = rag.load_chunks(d, "hierarchical")
        self.assertEqual(len(c), 1)
        
    def test_02_read_json_object(self):
        d = self.create_chunks_file({"chunks": [{"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "A"}]})
        c, _ = rag.load_chunks(d, "hierarchical")
        self.assertEqual(len(c), 1)
        
    def test_03_only_selected_strategy(self):
        d = self.create_chunks_file([
            {"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "A"},
            {"chunk_id": "2", "strategy": "semantic", "source": "s", "page_start": 1, "page_end": 1, "text": "A"}
        ])
        c, _ = rag.load_chunks(d, "hierarchical")
        self.assertEqual(len(c), 1)
        
    def test_04_missing_field(self):
        d = self.create_chunks_file([{"chunk_id": "1", "strategy": "hierarchical", "source": "s"}])
        with self.assertRaises(ValueError): rag.load_chunks(d, "hierarchical")
        
    def test_05_wrong_field_type(self):
        d = self.create_chunks_file([{"chunk_id": 123, "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "A"}])
        with self.assertRaises(ValueError): rag.load_chunks(d, "hierarchical")
        
    def test_06_boolean_page(self):
        d = self.create_chunks_file([{"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": True, "page_end": 1, "text": "A"}])
        with self.assertRaises(ValueError): rag.load_chunks(d, "hierarchical")
        
    def test_07_page_start_gt_page_end(self):
        d = self.create_chunks_file([{"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 2, "page_end": 1, "text": "A"}])
        with self.assertRaises(ValueError): rag.load_chunks(d, "hierarchical")
        
    def test_08_empty_text_skipped(self):
        d = self.create_chunks_file([{"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "   "}])
        c, s = rag.load_chunks(d, "hierarchical")
        self.assertEqual(len(c), 0)
        self.assertEqual(s['empty_text_skipped'], 1)
        
    def test_09_duplicate_chunk_id(self):
        d = self.create_chunks_file([
            {"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "A"},
            {"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "B"}
        ])
        with self.assertRaises(ValueError): rag.load_chunks(d, "hierarchical")
        
    def test_38_loader_rejects_non_object(self):
        d = self.create_chunks_file(["string"])
        with self.assertRaises(ValueError): rag.load_chunks(d, "hierarchical")

class TestIndexAndEmbedding(BaseTest):
    def test_10_index_twice(self):
        d = self.create_chunks_file([{"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "A"}])
        rag.do_index("hierarchical", reset=False, input_dir=d)
        r2 = rag.do_index("hierarchical", reset=False, input_dir=d)
        self.assertEqual(r2['count_after'], 1)
        
    def test_12_13_collection_identity(self):
        c1 = rag.get_collection_name("hierarchical", 128, "fake")
        c2 = rag.get_collection_name("semantic", 128, "fake")
        c3 = rag.get_collection_name("hierarchical", 256, "fake")
        self.assertNotEqual(c1, c2)
        self.assertNotEqual(c1, c3)
        
    def test_16_17_18_39_embedding_fail_modes(self):
        d = self.create_chunks_file([{"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "A"}])
        for mode in ['empty', 'wrong_dim', 'nan', 'boolean', 'zero']:
            MockGenAIClient.embed_fail_mode = mode
            with self.assertRaises(RuntimeError): rag.do_index("hierarchical", reset=False, input_dir=d)
            
    def test_19_error_before_upsert(self):
        d = self.create_chunks_file([{"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "A"}])
        MockGenAIClient.embed_fail_mode = 'nan'
        with self.assertRaises(RuntimeError): rag.do_index("hierarchical", reset=False, input_dir=d)
        col = self.chroma_client.get_or_create_collection(rag.get_collection_name("hierarchical", 128, "fake-embed"))
        self.assertEqual(col.count(), 0)
        
    def test_20_missing_api_key(self):
        d = self.create_chunks_file([{"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "A"}])
        rag.load_config.return_value['GEMINI_API_KEY'] = ''
        with self.assertRaises(ValueError): rag.do_index("hierarchical", reset=False, input_dir=d)
        
    def test_41_reset_preserves_old_on_embed_error(self):
        d = self.create_chunks_file([{"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "A"}])
        rag.do_index("hierarchical", reset=False, input_dir=d)
        MockGenAIClient.embed_fail_mode = 'nan'
        with self.assertRaises(RuntimeError): rag.do_index("hierarchical", reset=True, input_dir=d)
        col = self.chroma_client.get_collection(rag.get_collection_name("hierarchical", 128, "fake-embed"))
        self.assertEqual(col.count(), 1)
        
    def test_42_metadata_mismatch(self):
        c = rag.get_collection_name("hierarchical", 128, "fake-embed")
        self.chroma_client.create_collection(c, metadata={"strategy": "hierarchical", "embedding_dim": 999})
        d = self.create_chunks_file([{"chunk_id": "1", "strategy": "hierarchical", "source": "s", "page_start": 1, "page_end": 1, "text": "A"}])
        with self.assertRaises(Exception): rag.do_index("hierarchical", reset=False, input_dir=d)

class TestQueryAndGeneration(BaseTest):
    def setUp(self):
        super().setUp()
        self.d = self.create_chunks_file([
            {"chunk_id": "1", "strategy": "hierarchical", "source": "s1", "page_start": 1, "page_end": 1, "text": "A"},
            {"chunk_id": "2", "strategy": "hierarchical", "source": "s2", "page_start": 2, "page_end": 3, "text": "B"}
        ])
        rag.do_index("hierarchical", input_dir=self.d)
        
    def test_21_22_23_retrieval(self):
        res = rag.ask_question("test", top_k=1, strategy="hierarchical")
        self.assertEqual(len(res['evidence']), 1)
        res = rag.ask_question("test", top_k=5, strategy="hierarchical")
        self.assertEqual(len(res['evidence']), 2)
        dists = [e['distance'] for e in res['evidence']]
        self.assertEqual(dists, sorted(dists))
        
    def test_24_25_empty_and_bounds(self):
        with self.assertRaises(ValueError): rag.ask_question("   ", top_k=2, strategy="hierarchical")
        with self.assertRaises(ValueError): rag.ask_question("A", top_k=0, strategy="hierarchical")
        
    def test_27_28_confidence_gate(self):
        rag.load_config.return_value['RAG_MAX_DISTANCE'] = -1.0
        res = rag.ask_question("test", top_k=2, strategy="hierarchical")
        self.assertEqual(res['status'], 'insufficient_evidence')
        self.assertEqual(MockGenAIClient.generate_call_count, 0)
        
        rag.load_config.return_value['RAG_MAX_DISTANCE'] = 10.0
        res2 = rag.ask_question("test", top_k=2, strategy="hierarchical")
        self.assertEqual(res2['status'], 'answered')
        self.assertEqual(MockGenAIClient.generate_call_count, 1)
        
    def test_32_33_34_35_citation(self):
        MockGenAIClient.gen_text = "Dữ liệu [E1] và [E2] và [E99]"
        res = rag.ask_question("test", top_k=2, strategy="hierarchical")
        cites = res['citations']
        self.assertEqual(len(cites), 2)
        self.assertIn("tr.", cites[0]['display'])
        self.assertEqual(len(res['warnings']), 1)
        
    def test_36_46_generation_errors(self):
        MockGenAIClient.gen_fail = True
        res = rag.ask_question("test", top_k=2, strategy="hierarchical")
        self.assertEqual(res['status'], 'retrieval_only')
        
        MockGenAIClient.gen_fail = False
        MockGenAIClient.gen_text = "   "
        res2 = rag.ask_question("test", top_k=2, strategy="hierarchical")
        self.assertEqual(res2['status'], 'retrieval_only')

if __name__ == '__main__':
    unittest.main()
