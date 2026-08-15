import argparse
import sys
import os

# Add buoi_14 directory to sys.path to enable src imports
script_dir = os.path.dirname(os.path.abspath(__file__))
buoi14_dir = os.path.dirname(script_dir)
if buoi14_dir not in sys.path:
    sys.path.insert(0, buoi14_dir)

from src.hybrid_retriever import HybridRetriever
from src.reranker import CrossEncoderReranker


def main():
    parser = argparse.ArgumentParser(description="Hybrid Search + CrossEncoder Reranking - Buổi 14")
    parser.add_argument("--query", "-q", type=str, required=True, help="Câu hỏi tìm kiếm")
    parser.add_argument("--candidate-k", "-c", type=int, default=20, help="Số lượng candidates từ Hybrid Search (default: 20)")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Số lượng kết quả trả về sau Rerank (default: 5)")
    
    args = parser.parse_args()
    
    query = args.query
    candidate_k = args.candidate_k
    top_k = args.top_k
    
    print(f"QUERY: \"{query}\"")
    print(f"PIPELINE: Hybrid Candidate Retrieval (Top-{candidate_k}) -> CrossEncoder Reranking (Top-{top_k})\n")
    
    # Step 1: Hybrid Retrieval
    hybrid_retriever = HybridRetriever()
    candidates = hybrid_retriever.search(query, top_k=candidate_k, candidate_k=candidate_k)
    
    print("=" * 95)
    print(f" BEFORE RERANK (Hybrid Search Candidate Top-{min(10, len(candidates))}) ")
    print("=" * 95)
    print(f"{'Hybrid Rank':<12} | {'Chunk ID':<16} | {'RRF Score':<10} | {'Citation'}")
    print("-" * 95)
    for cand in candidates[:10]:
        print(f"{cand['final_rank']:<12} | {cand['chunk_id']:<16} | {cand['rrf_score']:<10.6f} | {cand['citation']}")
    print("-" * 95)
    
    # Step 2: CrossEncoder Reranking
    reranker = CrossEncoderReranker(model_name="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    reranked_results = reranker.rerank(query, candidates, top_k=top_k)
    
    print("\n" + "=" * 95)
    print(f" AFTER RERANK (CrossEncoder Scored Top-{top_k}) ")
    print("=" * 95)
    print(f"{'Final Rank':<10} | {'Chunk ID':<16} | {'Rerank Score':<12} | {'Hybrid Rank':<12} | {'Citation'}")
    print("-" * 95)
    for res in reranked_results:
        print(f"{res['final_rank']:<10} | {res['chunk_id']:<16} | {res['rerank_score']:<12.4f} | {res['hybrid_rank']:<12} | {res['citation']}")
    print("-" * 95)
    
    print("\nChi tiết nội dung Chunks sau Reranking:")
    for res in reranked_results:
        snippet = res['text'].replace('\n', ' ')
        if len(snippet) > 180:
            snippet = snippet[:180] + "..."
        print(f"\n[Rank {res['final_rank']}] {res['citation']} (Rerank Score: {res['rerank_score']})")
        print(f"Text: {snippet}")


if __name__ == "__main__":
    main()
