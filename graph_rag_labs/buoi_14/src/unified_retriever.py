import os
from typing import List, Dict
from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever
from src.hybrid_retriever import HybridRetriever
from src.reranker import CrossEncoderReranker


class UnifiedRetriever:
    def __init__(self):
        self.bm25 = BM25Retriever()
        self.dense = DenseRetriever()
        self.hybrid = HybridRetriever(bm25_retriever=self.bm25, dense_retriever=self.dense)
        self.reranker = CrossEncoderReranker()

    def retrieve(self, question: str, method: str = "hybrid_rerank", top_k: int = 5) -> List[Dict]:
        """
        Unified retrieval function supporting: 'bm25', 'dense', 'hybrid', 'hybrid_rerank'
        """
        method_lower = method.lower().strip()
        if method_lower not in ["bm25", "dense", "hybrid", "hybrid_rerank"]:
            raise ValueError(f"Invalid method '{method}'. Choose from: 'bm25', 'dense', 'hybrid', 'hybrid_rerank'")

        if method_lower == "bm25":
            raw_hits = self.bm25.search(question, top_k=top_k)
            return [
                {
                    "rank": item["rank"],
                    "chunk_id": item["chunk_id"],
                    "document_id": item["document_id"],
                    "text": item["text"],
                    "score": item["retrieval_score"],
                    "citation": item["citation"],
                    "retrieval_method": "bm25"
                }
                for item in raw_hits
            ]

        elif method_lower == "dense":
            raw_hits = self.dense.search(question, top_k=top_k)
            return [
                {
                    "rank": item["rank"],
                    "chunk_id": item["chunk_id"],
                    "document_id": item["document_id"],
                    "text": item["text"],
                    "score": item["retrieval_score"],
                    "citation": item["citation"],
                    "retrieval_method": "dense"
                }
                for item in raw_hits
            ]

        elif method_lower == "hybrid":
            raw_hits = self.hybrid.search(question, top_k=top_k, candidate_k=20)
            return [
                {
                    "rank": item["final_rank"],
                    "chunk_id": item["chunk_id"],
                    "document_id": item["document_id"],
                    "text": item["text"],
                    "score": item["rrf_score"],
                    "citation": item["citation"],
                    "retrieval_method": "hybrid"
                }
                for item in raw_hits
            ]

        elif method_lower == "hybrid_rerank":
            candidate_hits = self.hybrid.search(question, top_k=20, candidate_k=20)
            reranked_hits = self.reranker.rerank(question, candidate_hits, top_k=top_k)
            return [
                {
                    "rank": item["final_rank"],
                    "chunk_id": item["chunk_id"],
                    "document_id": item["document_id"],
                    "text": item["text"],
                    "score": item["rerank_score"],
                    "hybrid_score": item.get("hybrid_score", 0.0),
                    "rerank_score": item["rerank_score"],
                    "citation": item["citation"],
                    "retrieval_method": "hybrid_rerank"
                }
                for item in reranked_hits
            ]
