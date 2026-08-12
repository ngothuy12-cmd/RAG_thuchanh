import pandas as pd
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from bs4 import BeautifulSoup

# --- CẤU HÌNH ---
NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "abcd1234"
MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"

print("Đang khởi tạo kết nối Neo4j và tải mô hình...")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
model = SentenceTransformer(MODEL_NAME, device='cpu')

def xoa_du_lieu_cu():
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("Đã xóa dữ liệu cũ trong Neo4j.")

def nap_metadata():
    print("Đang nạp siêu dữ liệu (Document)...")
    df = pd.read_csv("kb+hops/metadata.csv").fillna("")
    
    query = """
    UNWIND $rows AS row
    MERGE (d:Document {id: row.id})
    SET d.title = row.title,
        d.so_ky_hieu = row.so_ky_hieu,
        d.ngay_ban_hanh = row.ngay_ban_hanh,
        d.loai_van_ban = row.loai_van_ban,
        d.co_quan_ban_hanh = row.co_quan_ban_hanh
    """
    with driver.session() as session:
        session.run(query, rows=df.to_dict('records'))

def nap_relationships():
    print("Đang nạp quan hệ giữa các Document...")
    df = pd.read_csv("kb+hops/relationships.csv").fillna("")
    
    with driver.session() as session:
        for _, row in df.iterrows():
            rel_type = row['relationship_type']
            query = f"""
            MATCH (d1:Document {{id: $doc_id}})
            MATCH (d2:Document {{id: $other_doc_id}})
            MERGE (d1)-[:{rel_type}]->(d2)
            """
            session.run(query, doc_id=row['doc_id'], other_doc_id=row['other_doc_id'])

def xu_ly_va_nap_chunks():
    print("Đang đọc HTML, tạo Vector Nhúng và nạp Chunk vào Neo4j...")
    df = pd.read_csv("kb+hops/content.csv").fillna("")
    
    with driver.session() as session:
        for index, row in df.iterrows():
            doc_id = row['id']
            html_content = row['content_html']
            
            # 1. Phân tách HTML (Chunking)
            soup = BeautifulSoup(html_content, 'html.parser')
            paragraphs = soup.find_all('p')
            
            chunks = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 20: 
                    chunks.append(text)
            
            if not chunks:
                continue
                
            print(f"  -> Xử lý văn bản ID {doc_id} ({len(chunks)} phân đoạn)...")
            
            # 2. Tạo Vector Nhúng (Embedding)
            embeddings = model.encode(chunks)
            
            # 3. Nạp vào Neo4j
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                embedding_list = embeddings[i].tolist() 
                
                # Nút Chunk và quan hệ PART_OF (thuộc văn bản nào)
                query_chunk = """
                MATCH (d:Document {id: $doc_id})
                MERGE (c:Chunk {id: $chunk_id})
                SET c.text = $text, c.embedding = $embedding
                MERGE (c)-[:PART_OF]->(d)
                """
                session.run(query_chunk, doc_id=doc_id, chunk_id=chunk_id, text=chunk_text, embedding=embedding_list)
                
                # Quan hệ NEXT (liên kết trình tự đọc)
                if i > 0:
                    prev_chunk_id = f"{doc_id}_chunk_{i-1}"
                    query_next = """
                    MATCH (prev:Chunk {id: $prev_id})
                    MATCH (curr:Chunk {id: $curr_id})
                    MERGE (prev)-[:NEXT]->(curr)
                    """
                    session.run(query_next, prev_id=prev_chunk_id, curr_id=chunk_id)
                
                # Quan hệ PARENT_OF (Giả lập: Chunk đầu tiên là cha của các chunk sau)
                if i > 0:
                    parent_chunk_id = f"{doc_id}_chunk_0"
                    query_parent = """
                    MATCH (parent:Chunk {id: $parent_id})
                    MATCH (child:Chunk {id: $child_id})
                    MERGE (parent)-[:PARENT_OF]->(child)
                    """
                    session.run(query_parent, parent_id=parent_chunk_id, child_id=chunk_id)

def main():
    xoa_du_lieu_cu()
    nap_metadata()
    nap_relationships()
    xu_ly_va_nap_chunks()
    
    print("HOÀN THÀNH TOÀN BỘ QUÁ TRÌNH!")
    driver.close()

if __name__ == "__main__":
    main()
