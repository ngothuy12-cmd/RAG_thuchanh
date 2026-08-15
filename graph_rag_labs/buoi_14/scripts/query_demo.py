import argparse
import sys
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Add buoi_14 directory to sys.path to enable src imports
script_dir = os.path.dirname(os.path.abspath(__file__))
buoi14_dir = os.path.dirname(script_dir)
root_dir = os.path.dirname(buoi14_dir)
if buoi14_dir not in sys.path:
    sys.path.insert(0, buoi14_dir)

from src.unified_retriever import UnifiedRetriever


def get_graph_hints(doc_ids: list, chunk_ids: list):
    """
    Fetches 1-hop direct graph relationships from Neo4j for retrieved documents & chunks.
    Does NOT perform multi-hop traversal.
    """
    env_path = os.path.join(root_dir, ".env")
    load_dotenv(env_path)
    
    uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    user = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
    password = os.getenv("NEO4J_PASSWORD", "abcd1234")
    db = os.getenv("NEO4J_DATABASE", "neo4j")
    
    graph_data = {
        "doc_relations": [],
        "chunk_next": []
    }
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session(database=db) as session:
            # Query 1: Direct 1-hop legal relations between VanBan nodes
            cypher_doc_rel = """
            MATCH (v1:VanBan {lab_session: 'buoi_14'})-[r]->(v2:VanBan {lab_session: 'buoi_14'})
            WHERE v1.id IN $doc_ids OR v2.id IN $doc_ids
              AND type(r) IN ['SUA_DOI_BO_SUNG', 'CAN_CU', 'THAY_THE', 'VAN_BAN_BO_SUNG', 'HOP_NHAT']
            RETURN v1.id AS SourceID, v1.so_ky_hieu AS SourceDoc, type(r) AS RelType, 
                   v2.id AS TargetID, v2.so_ky_hieu AS TargetDoc
            LIMIT 10
            """
            res_doc = session.run(cypher_doc_rel, doc_ids=[str(d) for d in doc_ids])
            for record in res_doc:
                graph_data["doc_relations"].append({
                    "source": f"VanBan ({record['SourceDoc'] or record['SourceID']})",
                    "rel": record['RelType'],
                    "target": f"VanBan ({record['TargetDoc'] or record['TargetID']})"
                })
                
            # Query 2: Direct 1-hop NEXT neighbor chunks
            cypher_chunk_next = """
            MATCH (d1:DieuKhoan {lab_session: 'buoi_14'})-[r:NEXT]->(d2:DieuKhoan {lab_session: 'buoi_14'})
            WHERE d1.id IN $chunk_ids
            RETURN d1.id AS CurrentChunk, d1.article AS CurrentArticle, d2.id AS NextChunk, d2.article AS NextArticle
            LIMIT 10
            """
            res_chunk = session.run(cypher_chunk_next, chunk_ids=[str(c) for c in chunk_ids])
            for record in res_chunk:
                graph_data["chunk_next"].append({
                    "current": f"{record['CurrentChunk']} ({record['CurrentArticle']})",
                    "next": f"{record['NextChunk']} ({record['NextArticle']})"
                })
                
        driver.close()
        return graph_data, True
    except Exception as e:
        return {"error": str(e)}, False


def main():
    parser = argparse.ArgumentParser(description="Unified Retrieval Demo & Graph Hints - Buổi 14")
    parser.add_argument("--query", "-q", type=str, required=True, help="Câu hỏi tìm kiếm")
    parser.add_argument("--method", "-m", type=str, default="hybrid_rerank",
                        choices=["bm25", "dense", "hybrid", "hybrid_rerank"],
                        help="Phương pháp retrieval (default: hybrid_rerank)")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Số lượng kết quả Top-K (default: 5)")
    
    args = parser.parse_args()
    
    query = args.query
    method = args.method
    top_k = args.top_k
    
    print(f"\nQUERY: \"{query}\"")
    print(f"METHOD: {method.upper()} | TOP-K: {top_k}\n")
    
    retriever = UnifiedRetriever()
    results = retriever.retrieve(question=query, method=method, top_k=top_k)
    
    print("=" * 95)
    print(f" RETRIEVAL RESULTS ({method.upper()}) ")
    print("=" * 95)
    
    if method == "hybrid_rerank":
        print(f"{'Rank':<6} | {'Chunk ID':<16} | {'Rerank Score':<12} | {'Hybrid Score':<12} | {'Citation'}")
        print("-" * 95)
        for res in results:
            h_score_str = f"{res.get('hybrid_score', 0.0):.6f}"
            r_score_str = f"{res.get('rerank_score', 0.0):.4f}"
            print(f"{res['rank']:<6} | {res['chunk_id']:<16} | {r_score_str:<12} | {h_score_str:<12} | {res['citation']}")
    else:
        print(f"{'Rank':<6} | {'Chunk ID':<16} | {'Score':<12} | {'Citation'}")
        print("-" * 95)
        for res in results:
            score_str = f"{res['score']:.4f}"
            print(f"{res['rank']:<6} | {res['chunk_id']:<16} | {score_str:<12} | {res['citation']}")
            
    print("-" * 95)
    
    print("\nChi tiết nội dung Context Trích dẫn:")
    for res in results:
        snippet = res['text'].replace('\n', ' ')
        if len(snippet) > 180:
            snippet = snippet[:180] + "..."
        print(f"\n[Rank {res['rank']}] {res['citation']} (Score: {res['score']})")
        print(f"Text: {snippet}")
        
    # Extract unique document_ids and chunk_ids for GRAPH HINTS
    retrieved_doc_ids = list(dict.fromkeys([res["document_id"] for res in results]))
    retrieved_chunk_ids = [res["chunk_id"] for res in results]
    
    print("\n" + "=" * 95)
    print(" GRAPH HINTS (Thông tin bổ trợ đồ thị cho bài Graph RAG tiếp theo) ")
    print("=" * 95)
    print(f"Retrieved Document IDs ({len(retrieved_doc_ids)}): {retrieved_doc_ids}")
    print(f"Retrieved Chunk IDs ({len(retrieved_chunk_ids)}): {retrieved_chunk_ids}\n")
    
    hints_data, is_neo4j_ok = get_graph_hints(retrieved_doc_ids, retrieved_chunk_ids)
    
    if is_neo4j_ok:
        print("[Status: Neo4j Connected]")
        print("\n1. Direct 1-hop Legal Document Relationships (Quan hệ pháp lý liên văn bản):")
        if hints_data["doc_relations"]:
            for rel in hints_data["doc_relations"]:
                print(f"  - {rel['source']} ==[{rel['rel']}]==> {rel['target']}")
        else:
            print("  (Không tìm thấy quan hệ pháp lý liên văn bản trực tiếp 1-hop trong tập kết quả)")
            
        print("\n2. Sequential NEXT Chunk Chains (Kế cận 1-hop điều khoản):")
        if hints_data["chunk_next"]:
            for chk in hints_data["chunk_next"]:
                print(f"  - {chk['current']} --[:NEXT]--> {chk['next']}")
        else:
            print("  (Không có thông tin chuỗi NEXT kế cận)")
    else:
        print("[Status: Neo4j Not Connected / Standalone Mode]")
        print(f"  Note: {hints_data.get('error', 'Neo4j unavailable')}")
        print("  Dữ liệu Retrieval đã sẵn sàng. Có thể nạp Neo4j để sử dụng Graph Hints.")
        
    print("=" * 95 + "\n")


if __name__ == "__main__":
    main()
