import argparse
import sys
import os

# Add buoi_14 directory to sys.path to enable src imports
script_dir = os.path.dirname(os.path.abspath(__file__))
buoi14_dir = os.path.dirname(script_dir)
if buoi14_dir not in sys.path:
    sys.path.insert(0, buoi14_dir)

from src.bm25_retriever import BM25Retriever
from src.dense_retriever import DenseRetriever


def print_results(title: str, results: list):
    print("\n" + "=" * 80)
    print(f" {title} ")
    print("=" * 80)
    if not results:
        print("No results found.")
        return
        
    for res in results:
        print(f"Rank {res['rank']} | Score: {res['retrieval_score']} | Method: {res['retrieval_method']}")
        print(f"Citation: {res['citation']}")
        print(f"Document ID: {res['document_id']} | Chunk ID: {res['chunk_id']}")
        snippet = res['text'].replace('\n', ' ')
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."
        print(f"Text: {snippet}")
        print("-" * 80)


def main():
    parser = argparse.ArgumentParser(description="Baseline Retrieval (BM25 vs Dense) - Buổi 14")
    parser.add_argument("--query", "-q", type=str, required=True, help="Câu hỏi tìm kiếm")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Số lượng kết quả top-k (default: 5)")
    
    args = parser.parse_args()
    
    query = args.query
    top_k = args.top_k
    
    print(f"QUERY: \"{query}\" (Top-K: {top_k})")
    
    # Run BM25 Retrieval
    bm25 = BM25Retriever()
    bm25_results = bm25.search(query, top_k=top_k)
    print_results("BM25 RESULTS", bm25_results)
    
    # Run Dense Retrieval
    dense = DenseRetriever()
    dense_results = dense.search(query, top_k=top_k)
    print_results("DENSE RESULTS", dense_results)


if __name__ == "__main__":
    main()
