import os
import json
import re
import numpy as np
import pandas as pd
from typing import List, Dict, Union
from neo4j import GraphDatabase

from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
from src.bm25_retriever import BM25Retriever, tokenize_text
from src.dense_retriever import DenseRetriever
from src.reranker import CrossEncoderReranker


def is_role_allowed(allowed_roles: Union[List[str], str], user_roles: List[str]) -> bool:
    """
    Checks if there is any intersection between user_roles and document's allowed_roles.
    Handles both list objects and JSON string representations.
    """
    if not user_roles:
        return False
        
    if isinstance(allowed_roles, str):
        try:
            roles_list = json.loads(allowed_roles)
        except Exception:
            roles_list = [allowed_roles]
    elif isinstance(allowed_roles, list):
        roles_list = allowed_roles
    else:
        roles_list = []
        
    # Check if any user role matches any allowed role
    return any(r in roles_list for r in user_roles)


class SecureRetriever:
    def __init__(self, csv_path: str = None):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        buoi14_dir = os.path.dirname(script_dir)
        
        if csv_path is None:
            csv_path = os.path.join(buoi14_dir, "data", "processed", "chunks_secure.csv")
            if not os.path.exists(csv_path):
                # Fallback if chunks_secure.csv doesn't exist yet
                csv_path = os.path.join(buoi14_dir, "data", "processed", "chunks_normalized.csv")

        print(f"Initializing SecureRetriever with dataset: {csv_path}")
        self.df = pd.read_csv(csv_path, encoding="utf-8").fillna("")
        
        # Ensure allowed_roles is parsed as Python list
        self.corpus_records = self.df.to_dict(orient="records")
        for rec in self.corpus_records:
            ar = rec.get("allowed_roles", "[]")
            if isinstance(ar, str):
                try:
                    rec["allowed_roles_list"] = json.loads(ar)
                except Exception:
                    rec["allowed_roles_list"] = ["Admin", "HR", "Risk_Manager", "Staff", "Guest"]
            elif isinstance(ar, list):
                rec["allowed_roles_list"] = ar
            else:
                rec["allowed_roles_list"] = ["Admin", "HR", "Risk_Manager", "Staff", "Guest"]

        # Initialize base retrievers and reranker
        self.bm25_base = BM25Retriever(csv_path=csv_path)
        self.dense_base = DenseRetriever(csv_path=csv_path)
        self.reranker = CrossEncoderReranker()
        
        # Database connection config
        self.neo4j_uri = NEO4J_URI
        self.neo4j_user = NEO4J_USER
        self.neo4j_password = NEO4J_PASSWORD
        self.neo4j_database = NEO4J_DATABASE

    def search_bm25(self, question: str, user_roles: List[str], top_k: int = 5) -> List[Dict]:
        """
        Secure BM25 Search: Scores all chunks, then filters candidates to ONLY those allowed for user_roles.
        """
        query_tokens = tokenize_text(question)
        if not query_tokens or not user_roles:
            return []
            
        scores = self.bm25_base.bm25.get_scores(query_tokens)
        sorted_indices = scores.argsort()[::-1]
        
        results = []
        rank = 1
        for idx in sorted_indices:
            rec = self.corpus_records[idx]
            allowed_roles = rec["allowed_roles_list"]
            
            if is_role_allowed(allowed_roles, user_roles):
                score = float(scores[idx])
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
                    "score": round(score, 4),
                    "retrieval_score": round(score, 4),
                    "allowed_roles": allowed_roles,
                    "citation": citation,
                    "retrieval_method": "bm25"
                })
                rank += 1
                if len(results) >= top_k:
                    break
                    
        return results

    def search_dense(self, question: str, user_roles: List[str], top_k: int = 5) -> List[Dict]:
        """
        Secure Dense Vector Search: Post-filters dense vector similarity search results by allowed_roles.
        """
        if not question.strip() or not user_roles:
            return []
            
        query_vector = self.dense_base.model.encode([question], normalize_embeddings=True)[0]
        scores = np.dot(self.dense_base.embeddings, query_vector)
        sorted_indices = np.argsort(scores)[::-1]
        
        results = []
        rank = 1
        for idx in sorted_indices:
            rec = self.corpus_records[idx]
            allowed_roles = rec["allowed_roles_list"]
            
            if is_role_allowed(allowed_roles, user_roles):
                score = float(scores[idx])
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
                    "score": round(score, 4),
                    "retrieval_score": round(score, 4),
                    "allowed_roles": allowed_roles,
                    "citation": citation,
                    "retrieval_method": "dense"
                })
                rank += 1
                if len(results) >= top_k:
                    break
                    
        return results

    def search_graph(self, question: str, user_roles: List[str], top_k: int = 5) -> List[Dict]:
        """
        Secure Graph Search (Neo4j): Executes Cypher query with explicit access filtering:
        WHERE any(role IN d.allowed_roles WHERE role IN $user_roles)
        """
        if not question.strip() or not user_roles:
            return []

        cypher = """
        MATCH (v:VanBan)-[:CONTAINS]->(d:DieuKhoan)
        WHERE any(role IN d.allowed_roles WHERE role IN $user_roles)
          AND (
            toLower(d.text) CONTAINS toLower($search_text) OR 
            toLower(v.title) CONTAINS toLower($search_text) OR 
            toLower(v.so_ky_hieu) CONTAINS toLower($search_text) OR
            toLower(d.article) CONTAINS toLower($search_text)
          )
        RETURN d.id AS chunk_id,
               d.document_id AS document_id,
               d.text AS text,
               d.article AS article,
               d.allowed_roles AS allowed_roles,
               v.title AS title,
               v.so_ky_hieu AS so_ky_hieu
        LIMIT $top_k
        """
        
        results = []
        try:
            driver = GraphDatabase.driver(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password))
            with driver.session(database=self.neo4j_database) as session:
                records = session.run(cypher, search_text=question, user_roles=user_roles, top_k=top_k).data()
                
                for rank, rec in enumerate(records, 1):
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
                        "score": 1.0,  # Match score indicator
                        "allowed_roles": rec.get("allowed_roles", []),
                        "citation": citation,
                        "retrieval_method": "graph"
                    })
            driver.close()
        except Exception as e:
            print(f"⚠️ Neo4j Graph Search Error: {e}")
            
        return results

    def search_hybrid(self, question: str, user_roles: List[str], top_k: int = 5, candidate_k: int = 20) -> List[Dict]:
        """
        Secure Hybrid Search: Fuses pre-filtered BM25 & Dense hits using Reciprocal Rank Fusion (RRF).
        """
        bm25_hits = self.search_bm25(question, user_roles=user_roles, top_k=candidate_k)
        dense_hits = self.search_dense(question, user_roles=user_roles, top_k=candidate_k)
        
        candidates = {}
        bm25_ranks = {hit["chunk_id"]: hit["rank"] for hit in bm25_hits}
        dense_ranks = {hit["chunk_id"]: hit["rank"] for hit in dense_hits}
        
        for hit in bm25_hits + dense_hits:
            cid = hit["chunk_id"]
            if cid not in candidates:
                candidates[cid] = hit
                
        rrf_k = 60
        hybrid_results = []
        for cid, record in candidates.items():
            r_bm25 = bm25_ranks.get(cid, None)
            r_dense = dense_ranks.get(cid, None)
            
            rrf_score = 0.0
            if r_bm25 is not None:
                rrf_score += 1.0 / (rrf_k + r_bm25)
            if r_dense is not None:
                rrf_score += 1.0 / (rrf_k + r_dense)
                
            hybrid_results.append({
                "chunk_id": cid,
                "document_id": record["document_id"],
                "text": record["text"],
                "score": round(rrf_score, 6),
                "rrf_score": round(rrf_score, 6),
                "bm25_rank": r_bm25,
                "dense_rank": r_dense,
                "allowed_roles": record["allowed_roles"],
                "citation": record["citation"],
                "retrieval_method": "hybrid"
            })
            
        hybrid_results.sort(key=lambda x: x["score"], reverse=True)
        for rank, item in enumerate(hybrid_results, 1):
            item["rank"] = rank
            item["final_rank"] = rank
            
        return hybrid_results[:top_k]

    def search_hybrid_rerank(self, question: str, user_roles: List[str], top_k: int = 5, candidate_k: int = 20) -> List[Dict]:
        """
        Secure Hybrid Rerank: Reranks candidate chunks with CrossEncoder.
        Input candidates are ALWAYS 100% pre-filtered by user_roles, ensuring 0 data leakage.
        """
        candidate_hits = self.search_hybrid(question, user_roles=user_roles, top_k=candidate_k, candidate_k=candidate_k)
        if not candidate_hits:
            return []
            
        reranked_hits = self.reranker.rerank(question, candidate_hits, top_k=top_k)
        
        results = []
        for rank, item in enumerate(reranked_hits, 1):
            results.append({
                "rank": rank,
                "final_rank": rank,
                "chunk_id": item["chunk_id"],
                "document_id": item["document_id"],
                "text": item["text"],
                "score": item["rerank_score"],
                "rerank_score": item["rerank_score"],
                "hybrid_score": item.get("hybrid_score", 0.0),
                "allowed_roles": item["allowed_roles"],
                "citation": item["citation"],
                "retrieval_method": "hybrid_rerank"
            })
        return results

    def retrieve(self, question: str, user_roles: List[str], method: str = "hybrid_rerank", top_k: int = 5) -> List[Dict]:
        """
        Unified Secure Retrieval interface supporting: 'bm25', 'dense', 'graph', 'hybrid', 'hybrid_rerank'.
        """
        method_lower = method.lower().strip()
        if method_lower == "bm25":
            return self.search_bm25(question, user_roles=user_roles, top_k=top_k)
        elif method_lower == "dense":
            return self.search_dense(question, user_roles=user_roles, top_k=top_k)
        elif method_lower == "graph":
            return self.search_graph(question, user_roles=user_roles, top_k=top_k)
        elif method_lower == "hybrid":
            return self.search_hybrid(question, user_roles=user_roles, top_k=top_k)
        elif method_lower in ["hybrid_rerank", "secure"]:
            return self.search_hybrid_rerank(question, user_roles=user_roles, top_k=top_k)
        else:
            raise ValueError(f"Unknown retrieval method '{method}'. Supported: 'bm25', 'dense', 'graph', 'hybrid', 'hybrid_rerank'")
