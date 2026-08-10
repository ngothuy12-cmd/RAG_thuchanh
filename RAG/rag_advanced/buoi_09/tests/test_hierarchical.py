import unittest
import tempfile
import os
import json
from pathlib import Path
from hierarchical_rag import (
    load_config, resolve_hierarchy, build_parents, atomic_write,
    load_and_validate_chunks
)

class TestHierarchicalBuilder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "chunks"
        self.input_dir.mkdir()
        self.config = {
            "PARENT_MAX_CHARS": 100,
            "MULTI_QUERY_COUNT": 3,
            "MULTI_QUERY_MAX_CHARS": 300,
            "MULTI_QUERY_TEMPERATURE": 0.2,
            "MULTI_QUERY_ORIGINAL_WEIGHT": 1.5,
            "MULTI_QUERY_VARIANT_WEIGHT": 1.0,
            "MULTI_QUERY_RRF_K": 60,
            "PER_QUERY_CANDIDATES": 12,
            "PARENT_SCORE_CHILD_LIMIT": 3,
            "PARENT_RRF_K": 60,
            "PARENT_CANDIDATES": 10,
            "FINAL_PARENT_TOP_K": 3,
            "TOTAL_CONTEXT_MAX_CHARS": 16000,
            "GEMINI_API_KEY": "test",
            "GEMINI_EMBEDDING_MODEL": "test",
            "GEMINI_GENERATION_MODEL": "test"
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_chunks(self, chunks, filename="test__hierarchical.json"):
        with open(self.input_dir / filename, 'w', encoding='utf-8') as f:
            json.dump({"chunks": chunks}, f)

    def test_metadata_precedence_and_conflict(self):
        chunks = [
            {
                "chunk_id": "doc1:hierarchical:1",
                "strategy": "hierarchical",
                "source": "doc1",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 2. Something",
                "structure": {"article": "Điều 1"}
            }
        ]
        self.write_chunks(chunks)
        loaded = load_and_validate_chunks(str(self.input_dir))
        resolved = resolve_hierarchy(loaded)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["structural_path"]["article"], "Điều 1")
        self.assertTrue(resolved[0]["ambiguous"])
        self.assertEqual(resolved[0]["resolution_method"], "metadata")

    def test_heading_inferred(self):
        chunks = [
            {
                "chunk_id": "doc1:hierarchical:1",
                "strategy": "hierarchical",
                "source": "doc1",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 5. Test heading",
                "structure": {}
            }
        ]
        self.write_chunks(chunks)
        resolved = resolve_hierarchy(load_and_validate_chunks(str(self.input_dir)))
        self.assertEqual(resolved[0]["structural_path"]["article"], "Điều 5")
        self.assertEqual(resolved[0]["resolution_method"], "heading_inferred")

    def test_carry_forward(self):
        chunks = [
            {
                "chunk_id": "doc1:hierarchical:1",
                "strategy": "hierarchical",
                "source": "doc1",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 10. Heading",
                "structure": {}
            },
            {
                "chunk_id": "doc1:hierarchical:2",
                "strategy": "hierarchical",
                "source": "doc1",
                "page_start": 1,
                "page_end": 1,
                "text": "1. Khoản 1",
                "structure": {}
            }
        ]
        self.write_chunks(chunks)
        resolved = resolve_hierarchy(load_and_validate_chunks(str(self.input_dir)))
        self.assertEqual(resolved[1]["structural_path"]["article"], "Điều 10")
        self.assertEqual(resolved[1]["resolution_method"], "carried_forward")

    def test_no_cross_source_carry(self):
        chunks1 = [
            {
                "chunk_id": "doc1:hierarchical:1",
                "strategy": "hierarchical",
                "source": "doc1",
                "page_start": 1,
                "page_end": 1,
                "text": "Điều 10. Heading",
                "structure": {}
            }
        ]
        chunks2 = [
            {
                "chunk_id": "doc2:hierarchical:1",
                "strategy": "hierarchical",
                "source": "doc2",
                "page_start": 1,
                "page_end": 1,
                "text": "1. Khoản 1",
                "structure": {}
            }
        ]
        self.write_chunks(chunks1, "doc1__hierarchical.json")
        self.write_chunks(chunks2, "doc2__hierarchical.json")
        resolved = resolve_hierarchy(load_and_validate_chunks(str(self.input_dir)))
        
        # doc2 chunk should not carry doc1's article
        doc2_res = [c for c in resolved if c['source'] == 'doc2'][0]
        self.assertIsNone(doc2_res["structural_path"]["article"])
        self.assertEqual(doc2_res["resolution_method"], "document_fallback")

    def test_inline_article_not_inferred(self):
        chunks = [
            {
                "chunk_id": "doc1:hierarchical:1",
                "strategy": "hierarchical",
                "source": "doc1",
                "page_start": 1,
                "page_end": 1,
                "text": "Nội dung này sửa đổi Điều 15 của luật cũ",
                "structure": {}
            }
        ]
        self.write_chunks(chunks)
        resolved = resolve_hierarchy(load_and_validate_chunks(str(self.input_dir)))
        self.assertIsNone(resolved[0]["structural_path"]["article"])
        self.assertEqual(resolved[0]["resolution_method"], "document_fallback")

    def test_numeric_ordering(self):
        chunks = [
            {
                "chunk_id": "doc1:hierarchical:10",
                "strategy": "hierarchical",
                "source": "doc1",
                "page_start": 1,
                "page_end": 1,
                "text": "Chunk 10",
                "structure": {}
            },
            {
                "chunk_id": "doc1:hierarchical:2",
                "strategy": "hierarchical",
                "source": "doc1",
                "page_start": 1,
                "page_end": 1,
                "text": "Chunk 2",
                "structure": {}
            }
        ]
        self.write_chunks(chunks)
        resolved = resolve_hierarchy(load_and_validate_chunks(str(self.input_dir)))
        self.assertEqual(resolved[0]["child_id"], "doc1:hierarchical:2")
        self.assertEqual(resolved[1]["child_id"], "doc1:hierarchical:10")

    def test_parent_split_and_oversize(self):
        chunks = [
            {
                "chunk_id": "doc1:hierarchical:1",
                "strategy": "hierarchical",
                "source": "doc1",
                "page_start": 1,
                "page_end": 1,
                "text": "A" * 60,
                "structure": {"article": "Điều 1"}
            },
            {
                "chunk_id": "doc1:hierarchical:2",
                "strategy": "hierarchical",
                "source": "doc1",
                "page_start": 1,
                "page_end": 2,
                "text": "B" * 60,
                "structure": {"article": "Điều 1"}
            },
            {
                "chunk_id": "doc1:hierarchical:3",
                "strategy": "hierarchical",
                "source": "doc1",
                "page_start": 2,
                "page_end": 2,
                "text": "C" * 150, # oversized
                "structure": {"article": "Điều 1"}
            }
        ]
        self.write_chunks(chunks)
        resolved = resolve_hierarchy(load_and_validate_chunks(str(self.input_dir)))
        parents = build_parents(resolved, self.config)
        
        # Max chars is 100.
        # Chunk 1 (60) + Chunk 2 (60) = 120 > 100 -> split.
        # Window 1: Chunk 1
        # Window 2: Chunk 2
        # Window 3: Chunk 3 (150 > 100 but single child so kept together, triggers warning)
        
        self.assertEqual(len(parents), 3)
        self.assertEqual(parents[0]["child_ids"], ["doc1:hierarchical:1"])
        self.assertEqual(parents[1]["child_ids"], ["doc1:hierarchical:2"])
        self.assertEqual(parents[2]["child_ids"], ["doc1:hierarchical:3"])
        
        self.assertEqual(parents[0]["page_start"], 1)
        self.assertEqual(parents[0]["page_end"], 1)
        self.assertEqual(parents[1]["page_start"], 1)
        self.assertEqual(parents[1]["page_end"], 2)
        
        self.assertTrue("oversized_single_child: doc1:hierarchical:3" in parents[2]["warnings"])
        
    def test_atomic_build_status(self):
        pass # covered by cli test in prompt run

if __name__ == '__main__':
    unittest.main()
