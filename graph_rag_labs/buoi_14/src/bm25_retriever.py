import os
import re
import pandas as pd
from rank_bm25 import BM25Okapi


def tokenize_text(text: str):
    """
    Tokenizes text while preserving:
    - Legal document codes (e.g., 01/2014/TT-NHNN, 73/2016/NĐ-CP)
    - Article & Clause identifiers (e.g., Điều 1, Khoản 2)
    - Vietnamese words
    """
    if not isinstance(text, str):
        return []
    text_lower = text.lower()
    # Pattern matches document numbers with slashes/dashes or regular word tokens
    pattern = r'\d+/\d+/[a-zàáảãạăắằẳẵặâấầnẩẫậeéèẻẽẹêếềểễệiíìỉĩịoóòỏõọôốồổỗộơớờởỡợuúùủũụưứừửữựyýỳỷỹỵđ\-\+]+|\w+'
    return re.findall(pattern, text_lower)


class BM25Retriever:
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            buoi14_dir = os.path.dirname(script_dir)
            csv_path = os.path.join(buoi14_dir, "data", "processed", "chunks_normalized.csv")
            
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Corpus file not found at: {csv_path}. Please run prepare_corpus.py first.")
            
        self.df = pd.read_csv(csv_path, encoding="utf-8").fillna("")
        self.corpus_records = self.df.to_dict(orient="records")
        
        # Tokenize corpus for BM25
        print("Indexing corpus with BM25...")
        self.tokenized_corpus = [
            tokenize_text(f"{row.get('so_ky_hieu', '')} {row.get('article', '')} {row.get('text', '')}")
            for row in self.corpus_records
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        print(f"BM25 Index built successfully with {len(self.corpus_records)} chunks.")

    def search(self, question: str, top_k: int = 5):
        query_tokens = tokenize_text(question)
        if not query_tokens:
            return []
            
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k indices sorted by score descending
        top_indices = scores.argsort()[::-1][:top_k]
        
        results = []
        for rank, idx in enumerate(top_indices, 1):
            score = float(scores[idx])
            rec = self.corpus_records[idx]
            
            # Format real citation
            so_ky_hieu = rec.get("so_ky_hieu", "")
            title = rec.get("title", "")
            doc_name = f"Số {so_ky_hieu}" if so_ky_hieu else title
            article = rec.get("article", "")
            chunk_id = rec.get("chunk_id", "")
            citation = f"[{doc_name} | {article} | {chunk_id}]"
            
            results.append({
                "rank": rank,
                "chunk_id": chunk_id,
                "document_id": str(rec.get("document_id", "")),
                "text": rec.get("text", ""),
                "retrieval_score": round(score, 4),
                "retrieval_method": "bm25",
                "citation": citation
            })
            
        return results
