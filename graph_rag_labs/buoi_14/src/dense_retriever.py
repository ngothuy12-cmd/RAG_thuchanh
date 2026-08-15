import os
import pickle
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


class DenseRetriever:
    def __init__(self, csv_path: str = None, model_name: str = "bkai-foundation-models/vietnamese-bi-encoder", cache_dir: str = None):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        buoi14_dir = os.path.dirname(script_dir)
        
        if csv_path is None:
            csv_path = os.path.join(buoi14_dir, "data", "processed", "chunks_normalized.csv")
            
        if cache_dir is None:
            cache_dir = os.path.join(buoi14_dir, "cache")
            
        os.makedirs(cache_dir, exist_ok=True)
        
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Corpus file not found at: {csv_path}. Please run prepare_corpus.py first.")
            
        self.df = pd.read_csv(csv_path, encoding="utf-8").fillna("")
        self.corpus_records = self.df.to_dict(orient="records")
        
        self.model_name = model_name
        print(f"Loading embedding model: {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)
        
        self.cache_embeddings_path = os.path.join(cache_dir, "dense_embeddings.npy")
        self.cache_meta_path = os.path.join(cache_dir, "dense_meta.pkl")
        
        # Load embeddings from cache if valid
        if os.path.exists(self.cache_embeddings_path) and os.path.exists(self.cache_meta_path):
            print(f"Loading cached dense embeddings from: {cache_dir}")
            self.embeddings = np.load(self.cache_embeddings_path)
            with open(self.cache_meta_path, "rb") as f:
                cached_chunk_ids = pickle.load(f)
            # Verify cache matches current corpus size
            if len(cached_chunk_ids) != len(self.corpus_records):
                print("Cache mismatch detected. Re-building dense index...")
                self._build_and_cache(cache_dir)
        else:
            print("No cache found. Building dense embeddings index...")
            self._build_and_cache(cache_dir)

    def _build_and_cache(self, cache_dir: str):
        # Prepare text for embedding (combine title/article with text)
        texts_to_embed = [
            f"{row.get('so_ky_hieu', '')} {row.get('article', '')}\n{row.get('text', '')}".strip()
            for row in self.corpus_records
        ]
        
        print(f"Encoding {len(texts_to_embed)} chunks into dense vectors...")
        embeddings_raw = self.model.encode(texts_to_embed, show_progress_bar=True, normalize_embeddings=True)
        self.embeddings = np.array(embeddings_raw, dtype=np.float32)
        
        chunk_ids = [row.get("chunk_id", "") for row in self.corpus_records]
        
        np.save(self.cache_embeddings_path, self.embeddings)
        with open(self.cache_meta_path, "wb") as f:
            pickle.dump(chunk_ids, f)
            
        print(f"Dense index saved to cache: {cache_dir}")

    def search(self, question: str, top_k: int = 5):
        if not question.strip():
            return []
            
        query_vector = self.model.encode([question], normalize_embeddings=True)[0]
        
        # Calculate cosine similarity (dot product of normalized vectors)
        scores = np.dot(self.embeddings, query_vector)
        
        # Top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
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
                "retrieval_method": "dense",
                "citation": citation
            })
            
        return results
