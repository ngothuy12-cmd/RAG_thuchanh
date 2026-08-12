import unittest
import os
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path
from advanced_rag import semantic_search, cmd_status
from rag import get_chroma_client, verify_or_create_collection, get_collection_name

class TestSemantic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(__file__).resolve().parent / "temp_chroma"
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)
            
    @classmethod
    def tearDownClass(cls):
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)
            
    def setUp(self):
        self.client = get_chroma_client(storage_path=self.temp_dir)
        self.col_name = get_collection_name("hierarchical", 768, "gemini-embedding-2")
        try:
            self.client.delete_collection(name=self.col_name)
        except Exception:
            pass
            
        config = {
            'GEMINI_EMBEDDING_MODEL': 'gemini-embedding-2',
            'GEMINI_EMBEDDING_DIM': 768
        }
        self.col = verify_or_create_collection(self.client, self.col_name, "hierarchical", config)
        
        self.col.upsert(
            ids=["chunk_1", "chunk_2", "chunk_3"],
            embeddings=[[0.1]*768, [1.0]*768, [-0.5]*768],
            documents=["Text 1", "Text 2", "Text 3"],
            metadatas=[
                {'chunk_id': 'chunk_1', 'source': 'A', 'page_start': 1, 'page_end': 1, 'strategy': 'hierarchical', 'embedding_model': 'gemini-embedding-2', 'embedding_dim': 768},
                {'chunk_id': 'chunk_2', 'source': 'B', 'page_start': 2, 'page_end': 2, 'strategy': 'hierarchical', 'embedding_model': 'gemini-embedding-2', 'embedding_dim': 768},
                {'chunk_id': 'chunk_3', 'source': 'C', 'page_start': 3, 'page_end': 3, 'strategy': 'hierarchical', 'embedding_model': 'gemini-embedding-2', 'embedding_dim': 768}
            ]
        )
        
    def tearDown(self):
        self.client.delete_collection(name=self.col_name)

    @patch('advanced_rag.genai.Client')
    @patch('advanced_rag.get_chroma_client')
    @patch('advanced_rag.load_config')
    def test_01_top_k_count_order_and_metadata(self, mock_load, mock_get_chroma, mock_genai):
        mock_load.return_value = {
            'GEMINI_API_KEY': 'fake_key',
            'GEMINI_EMBEDDING_MODEL': 'gemini-embedding-2',
            'GEMINI_EMBEDDING_DIM': 768
        }
        mock_get_chroma.return_value = self.client
        
        mock_client_instance = MagicMock()
        mock_genai.return_value = mock_client_instance
        mock_resp = MagicMock()
        mock_emb = MagicMock()
        
        # mock query embedding to perfectly match chunk_1
        mock_emb.values = [0.1]*768
        mock_resp.embeddings = [mock_emb]
        mock_client_instance.models.embed_content.return_value = mock_resp
        
        candidates = semantic_search("question", candidate_k=2, strategy="hierarchical")
        
        # 1. semantic top-k/count/order đúng
        self.assertEqual(len(candidates), 2)
        
        # 2. metadata đầy đủ
        self.assertIn("chunk_id", candidates[0])
        self.assertIn("text", candidates[0])
        self.assertIn("source", candidates[0])
        self.assertIn("semantic_distance", candidates[0])
        self.assertIn("semantic_rank", candidates[0])
        self.assertLessEqual(candidates[0]["semantic_distance"], candidates[1]["semantic_distance"])
        
        # 6. không gọi generation (chỉ gọi embed_content)
        mock_client_instance.models.embed_content.assert_called_once()
        mock_client_instance.models.generate_content.assert_not_called()

    @patch('advanced_rag.get_chroma_client')
    @patch('advanced_rag.load_config')
    def test_03_collection_mismatch_blocked(self, mock_load, mock_get_chroma):
        # Mismatch metadata!
        mock_load.return_value = {
            'GEMINI_API_KEY': 'fake_key',
            'GEMINI_EMBEDDING_MODEL': 'gemini-embedding-2',
            'GEMINI_EMBEDDING_DIM': 1234 # Wrong dimension
        }
        mock_get_chroma.return_value = self.client
        
        with self.assertRaises(ValueError):
            semantic_search("question", 2, "hierarchical")
            
    @patch('advanced_rag.load_config')
    @patch('advanced_rag.get_chroma_client')
    def test_05_no_key_fails_no_fake_vector(self, mock_get_chroma, mock_load):
        mock_load.return_value = {
            'GEMINI_API_KEY': '',
            'GEMINI_EMBEDDING_MODEL': 'gemini-embedding-2',
            'GEMINI_EMBEDDING_DIM': 768
        }
        mock_get_chroma.return_value = self.client
        
        with self.assertRaises(ValueError) as e:
            semantic_search("question", 2, "hierarchical")
        self.assertIn("Thiếu GEMINI_API_KEY", str(e.exception))
        
    @patch('advanced_rag.get_chroma_client')
    @patch('advanced_rag.load_config')
    def test_04_status_does_not_create_collection(self, mock_load, mock_get_chroma):
        mock_load.return_value = {
            'GEMINI_API_KEY': '',
            'GEMINI_EMBEDDING_MODEL': 'gemini-embedding-99',
            'GEMINI_EMBEDDING_DIM': 123,
            'RERANKER_MODEL': 'BAAI'
        }
        
        class FakeArgs:
            strategy = "semantic"
            input = "dummy"
            
        # Verify collection count before
        client = get_chroma_client(storage_path=self.temp_dir)
        initial_collections = client.list_collections()
        
        mock_get_chroma.return_value = client
        cmd_status(FakeArgs())
        
        # Verify collection count after - must be the same
        self.assertEqual(len(client.list_collections()), len(initial_collections))

if __name__ == '__main__':
    unittest.main()
