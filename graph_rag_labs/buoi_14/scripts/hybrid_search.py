import argparse
import sys
import os

# Add buoi_14 directory to sys.path to enable src imports
script_dir = os.path.dirname(os.path.abspath(__file__))
buoi14_dir = os.path.dirname(script_dir)
if buoi14_dir not in sys.path:
    sys.path.insert(0, buoi14_dir)

from src.hybrid_retriever import HybridRetriever


def main():
    parser = argparse.ArgumentParser(description="Hybrid Search (BM25 + Dense RRF) - Buổi 14")
    parser.add_argument("--query", "-q", type=str, required=True, help="Câu hỏi tìm kiếm")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Số lượng kết quả top-k trả về (default: 5)")
    parser.add_argument("--candidate-k", "-c", type=int, default=20, help="Số lượng candidate từ mỗi retriever (default: 20)")
    
    args = parser.parse_args()
    
    query = args.query
    top_k = args.top_k
    candidate_k = args.candidate_k
    
    print(f"HYBRID SEARCH QUERY: \"{query}\" (Candidate-K: {candidate_k}, Top-K: {top_k})")
    
    hybrid = HybridRetriever()
    results = hybrid.search(query, top_k=top_k, candidate_k=candidate_k)
    
    print("\n" + "=" * 95)
    print(" HYBRID RESULTS (Reciprocal Rank Fusion) ")
    print("=" * 95)
    print(f"{'Rank':<6} | {'Chunk ID':<16} | {'BM25 rank':<10} | {'Dense rank':<10} | {'RRF Score':<10} | {'Citation'}")
    print("-" * 95)
    
    for res in results:
        bm25_str = str(res['bm25_rank']) if res['bm25_rank'] is not None else "-"
        dense_str = str(res['dense_rank']) if res['dense_rank'] is not None else "-"
        print(f"{res['final_rank']:<6} | {res['chunk_id']:<16} | {bm25_str:<10} | {dense_str:<10} | {res['rrf_score']:<10.6f} | {res['citation']}")
        
    print("-" * 95)
    print("\nChi tiết nội dung Top chunks:")
    for res in results:
        snippet = res['text'].replace('\n', ' ')
        if len(snippet) > 180:
            snippet = snippet[:180] + "..."
        print(f"\n[Rank {res['final_rank']}] {res['citation']}")
        print(f"Text: {snippet}")


if __name__ == "__main__":
    main()
