import os
from typing import List, Dict
from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever


class HybridRetriever:
    def __init__(self, bm25_retriever: BM25Retriever = None, dense_retriever: DenseRetriever = None, rrf_k: int = 60):
        self.bm25 = bm25_retriever if bm25_retriever is not None else BM25Retriever()
        self.dense = dense_retriever if dense_retriever is not None else DenseRetriever()
        self.rrf_k = rrf_k

    def search(self, question: str, top_k: int = 5, candidate_k: int = 20) -> List[Dict]:
        """
        Performs Hybrid Search combining BM25 and Dense Retrieval using Reciprocal Rank Fusion (RRF).
        """
        if not question.strip():
            return []
            
        # Retrieve candidates from both retrievers
        bm25_hits = self.bm25.search(question, top_k=candidate_k)
        dense_hits = self.dense.search(question, top_k=candidate_k)
        
        # Maps chunk_id to candidate record
        candidates = {}
        
        # Track rank in BM25
        bm25_ranks = {}
        for hit in bm25_hits:
            cid = hit["chunk_id"]
            bm25_ranks[cid] = hit["rank"]
            candidates[cid] = hit
            
        # Track rank in Dense
        dense_ranks = {}
        for hit in dense_hits:
            cid = hit["chunk_id"]
            dense_ranks[cid] = hit["rank"]
            if cid not in candidates:
                candidates[cid] = hit
                
        # Calculate RRF score for each merged candidate
        hybrid_results = []
        for cid, record in candidates.items():
            r_bm25 = bm25_ranks.get(cid, None)
            r_dense = dense_ranks.get(cid, None)
            
            rrf_score = 0.0
            if r_bm25 is not None:
                rrf_score += 1.0 / (self.rrf_k + r_bm25)
            if r_dense is not None:
                rrf_score += 1.0 / (self.rrf_k + r_dense)
                
            hybrid_results.append({
                "chunk_id": cid,
                "document_id": record["document_id"],
                "bm25_rank": r_bm25,
                "dense_rank": r_dense,
                "rrf_score": round(rrf_score, 6),
                "text": record["text"],
                "citation": record["citation"]
            })
            
        # Sort by RRF score descending
        hybrid_results.sort(key=lambda x: x["rrf_score"], reverse=True)
        
        # Assign final_rank
        for rank, item in enumerate(hybrid_results, 1):
            item["final_rank"] = rank
            
        return hybrid_results[:top_k]
