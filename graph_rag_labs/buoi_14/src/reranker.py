import os
from typing import List, Dict
from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"):
        self.model_name = model_name
        print(f"Loading CrossEncoder Reranker model: {self.model_name}...")
        self.model = CrossEncoder(self.model_name)
        print("CrossEncoder model loaded successfully.")

    def rerank(self, question: str, candidates: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Reranks a list of candidate chunks returned by Hybrid Search using CrossEncoder.
        """
        if not candidates or not question.strip():
            return []
            
        # Form (query, candidate_text) pairs
        pairs = []
        for cand in candidates:
            # Combine citation header / article with text for best reranking context
            text_context = f"{cand.get('citation', '')}\n{cand.get('text', '')}"
            pairs.append((question, text_context))
            
        # Predict relevance scores
        scores = self.model.predict(pairs)
        
        reranked_candidates = []
        for cand, score in zip(candidates, scores):
            rec = dict(cand)
            rec["rerank_score"] = round(float(score), 4)
            rec["hybrid_rank"] = cand.get("final_rank", cand.get("bm25_rank", 0))
            rec["hybrid_score"] = cand.get("rrf_score", 0.0)
            reranked_candidates.append(rec)
            
        # Sort by rerank_score descending
        reranked_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        # Assign final_rank after reranking
        for rank, item in enumerate(reranked_candidates, 1):
            item["final_rank"] = rank
            
        return reranked_candidates[:top_k]
