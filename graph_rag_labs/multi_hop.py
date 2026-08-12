import os
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

class MultiHopRAG:
    def __init__(self, uri, user, password, model_name):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.model = SentenceTransformer(model_name, device='cpu')
        
    def close(self):
        self.driver.close()
        
    def create_vector_index(self):
        """
        Tạo vector index cho Neo4j nếu chưa có.
        Kích thước vector = 384 (phù hợp với mô hình thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5)
        """
        query = """
        CREATE VECTOR INDEX chunk_embedding_index IF NOT EXISTS
        FOR (c:Chunk) ON (c.embedding)
        OPTIONS {indexConfig: {
         `vector.dimensions`: 384,
         `vector.similarity_function`: 'cosine'
        }}
        """
        with self.driver.session() as session:
            session.run(query)
            print("Đã kiểm tra/tạo Vector Index 'chunk_embedding_index'.")
            
    def search_context(self, question, top_k=3, hops=1):
        """
        Tìm kiếm ngữ cảnh đa bước (multi-hop).
        - question: câu hỏi của người dùng
        - top_k: số lượng phân đoạn (chunk) khớp vector tốt nhất (khớp gốc)
        - hops: số bước nhảy (để mở rộng ngữ cảnh qua các văn bản liên quan)
        """
        # 1. Chuyển đổi câu hỏi thành vector nhúng
        question_embedding = self.model.encode(question).tolist()
        
        # Xây dựng truy vấn dựa trên cấu hình số bước nhảy
        if hops == 0:
            hop_pattern = ""
        else:
            # Duyệt qua các mối quan hệ luật: CAN_CU, THAY_THE, HOP_NHAT, SUA_DOI_BO_SUNG, VAN_BAN_BO_SUNG
            hop_pattern = f"-[:CAN_CU|THAY_THE|HOP_NHAT|SUA_DOI_BO_SUNG|VAN_BAN_BO_SUNG*1..{hops}]-(rel_d:Document)"

        # 1. Tìm kiếm Vector: Lấy top_k chunk phù hợp nhất
        vector_query = """
        CALL db.index.vector.queryNodes('chunk_embedding_index', $top_k, $question_embedding) 
        YIELD node AS c, score
        MATCH (c)-[:PART_OF]->(d:Document)
        RETURN score, c.id AS chunk_id, c.text AS text, d.id AS doc_id, d.title AS title
        """
        
        results = []
        matched_doc_ids = set()
        
        with self.driver.session() as session:
            vector_res = session.run(vector_query, question_embedding=question_embedding, top_k=top_k)
            for record in vector_res:
                matched_doc_ids.add(record["doc_id"])
                results.append({
                    "score": record["score"],
                    "chunk_id": record["chunk_id"],
                    "text": record["text"],
                    "doc_id": record["doc_id"],
                    "title": record["title"],
                    "type": 'Trực tiếp (Vector Match)'
                })
                
            # 2. Tìm kiếm đa bước nếu hops > 0
            if hops > 0 and matched_doc_ids:
                hop_pattern = f"-[:CAN_CU|THAY_THE|HOP_NHAT|SUA_DOI_BO_SUNG|VAN_BAN_BO_SUNG*1..{hops}]-(rel_d:Document)"
                hop_query = f"""
                UNWIND $doc_ids AS doc_id
                MATCH (d:Document {{id: doc_id}}){hop_pattern}
                WITH DISTINCT rel_d
                // Lọc bỏ các document đã nằm trong kết quả trực tiếp để tránh trùng lặp
                WHERE NOT rel_d.id IN $doc_ids
                
                MATCH (rel_c:Chunk)-[:PART_OF]->(rel_d)
                WITH rel_d, rel_c ORDER BY rel_c.id
                WITH rel_d, collect(rel_c)[0..2] AS rel_chunks
                
                UNWIND rel_chunks AS rc
                RETURN rc.id AS chunk_id, rc.text AS text, rel_d.id AS doc_id, rel_d.title AS title
                """
                hop_res = session.run(hop_query, doc_ids=list(matched_doc_ids))
                for record in hop_res:
                    results.append({
                        "score": 0.0,
                        "chunk_id": record["chunk_id"],
                        "text": record["text"],
                        "doc_id": record["doc_id"],
                        "title": record["title"],
                        "type": f'Liên quan (Multi-hop {hops} bước)'
                    })
                    
        return results

if __name__ == "__main__":
    NEO4J_URI = "bolt://127.0.0.1:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "abcd1234"
    MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"

    print("Đang khởi tạo hệ thống RAG và tải mô hình...")
    rag = MultiHopRAG(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, MODEL_NAME)
    rag.create_vector_index()
    
    question = "Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào?"
    print(f"\n--- Kiểm thử truy vấn: '{question}' ---")
    
    print("\n1. Kết quả với 0 bước nhảy (chỉ Vector):")
    context_0 = rag.search_context(question, top_k=2, hops=0)
    for i, ctx in enumerate(context_0):
        print(f" - [{ctx['type']}] {ctx['title']}: {ctx['text'][:150]}...")
        
    print("\n2. Kết quả với 1 bước nhảy (Multi-hop):")
    context_1 = rag.search_context(question, top_k=2, hops=1)
    for i, ctx in enumerate(context_1):
        print(f" - [{ctx['type']}] {ctx['title']}: {ctx['text'][:150]}...")
        
    rag.close()
    print("\nHoàn tất kiểm thử.")
