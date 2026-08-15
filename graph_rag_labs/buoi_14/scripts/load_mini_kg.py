import os
import sys
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Add buoi_14 directory to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
buoi14_dir = os.path.dirname(script_dir)
root_dir = os.path.dirname(buoi14_dir)

# Load .env configuration
env_path = os.path.join(root_dir, ".env")
load_dotenv(env_path)


def load_mini_knowledge_graph():
    uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    user = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
    password = os.getenv("NEO4J_PASSWORD", "abcd1234")
    db = os.getenv("NEO4J_DATABASE", "neo4j")
    
    print(f"Connecting to Neo4j at {uri} (Database: {db})...")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session(database=db) as session:
            session.run("RETURN 1")
        print("Connected to Neo4j successfully!")
    except Exception as e:
        print(f"ERROR: Cannot connect to Neo4j database: {e}")
        print("Please check if your Neo4j service is running and credentials in .env are correct.")
        sys.exit(1)

    # Base paths
    source_dir = os.path.join(root_dir, "kb+hops")
    meta_path = os.path.join(source_dir, "metadata.csv")
    rel_path = os.path.join(source_dir, "relationships.csv")
    chunks_path = os.path.join(buoi14_dir, "data", "processed", "chunks_normalized.csv")
    
    if not os.path.exists(chunks_path):
        raise FileNotFoundError(f"Missing {chunks_path}. Please run prepare_corpus.py first.")

    output_report = os.path.join(buoi14_dir, "outputs", "kg_build_report.md")

    with driver.session(database=db) as session:
        # Step 1: Safe Cleanup of previous Buổi 14 nodes/edges ONLY
        print("\nCleaning up existing nodes/edges with lab_session='buoi_14'...")
        session.run("MATCH (n {lab_session: 'buoi_14'}) DETACH DELETE n;")

        # Step 2: Apply Constraints and Indexes
        print("Applying Schema Constraints & Indexes...")
        schema_file = os.path.join(buoi14_dir, "cypher", "schema.cypher")
        if os.path.exists(schema_file):
            with open(schema_file, "r", encoding="utf-8") as f:
                queries = [q.strip() for q in f.read().split(";") if q.strip() and not q.strip().startswith("//")]
                for q in queries:
                    try:
                        session.run(q)
                    except Exception as ex:
                        print(f"Schema notice: {ex}")

        # Step 3: Load VanBan nodes from metadata.csv
        print(f"Loading VanBan nodes from: {meta_path}...")
        df_meta = pd.read_csv(meta_path, encoding="utf-8").fillna("")
        meta_records = df_meta.to_dict(orient="records")
        
        cypher_vanban = """
        UNWIND $records AS row
        MERGE (v:VanBan {id: toString(row.id)})
        SET v.title = row.title,
            v.so_ky_hieu = row.so_ky_hieu,
            v.document_type = row.loai_van_ban,
            v.status = row.tinh_trang_hieu_luc,
            v.co_quan_ban_hanh = row.co_quan_ban_hanh,
            v.ngay_ban_hanh = row.ngay_ban_hanh,
            v.lab_session = 'buoi_14'
        """
        session.run(cypher_vanban, records=meta_records)
        print(f"Loaded {len(meta_records)} VanBan nodes.")

        # Step 4: Load DieuKhoan nodes and CONTAINS & NEXT relationships
        print(f"Loading DieuKhoan nodes and relationships from: {chunks_path}...")
        df_chunks = pd.read_csv(chunks_path, encoding="utf-8").fillna("")
        
        # Batch insert DieuKhoan and CONTAINS relation
        cypher_dieukhoan = """
        UNWIND $records AS row
        MERGE (d:DieuKhoan {id: toString(row.chunk_id)})
        SET d.document_id = toString(row.document_id),
            d.text = row.text,
            d.article = row.article,
            d.chapter = row.chapter,
            d.section = row.section,
            d.lab_session = 'buoi_14'
            
        WITH d, row
        MATCH (v:VanBan {id: toString(row.document_id), lab_session: 'buoi_14'})
        MERGE (v)-[r:CONTAINS]->(d)
        SET r.lab_session = 'buoi_14'
        """
        chunk_records = df_chunks.to_dict(orient="records")
        session.run(cypher_dieukhoan, records=chunk_records)
        print(f"Loaded {len(chunk_records)} DieuKhoan nodes and CONTAINS relationships.")

        # Link sequential NEXT relationships between consecutive chunks of each document
        print("Linking sequential NEXT relationships between consecutive chunks...")
        cypher_next = """
        UNWIND $doc_ids AS docId
        MATCH (v:VanBan {id: docId, lab_session: 'buoi_14'})-[:CONTAINS]->(d:DieuKhoan)
        WITH docId, d ORDER BY d.id
        WITH docId, collect(d) AS chunkList
        UNWIND range(0, size(chunkList)-2) AS idx
        WITH chunkList[idx] AS d1, chunkList[idx+1] AS d2
        MERGE (d1)-[r:NEXT]->(d2)
        SET r.lab_session = 'buoi_14'
        """
        unique_doc_ids = [str(did) for did in df_chunks["document_id"].unique()]
        session.run(cypher_next, doc_ids=unique_doc_ids)

        # Step 5: Load legal relationships between VanBan nodes from relationships.csv
        print(f"Loading Inter-Document Relationships from: {rel_path}...")
        df_rel = pd.read_csv(rel_path, encoding="utf-8").fillna("")
        rel_records = df_rel.to_dict(orient="records")
        
        cypher_inter_doc = """
        UNWIND $records AS row
        MATCH (src:VanBan {id: toString(row.doc_id), lab_session: 'buoi_14'})
        MATCH (tgt:VanBan {id: toString(row.other_doc_id), lab_session: 'buoi_14'})
        WITH src, tgt, row
        CALL apoc.create.relationship(src, row.relationship_type, {relationship: row.relationship, lab_session: 'buoi_14'}, tgt)
        YIELD rel
        RETURN count(rel)
        """
        # Fallback query if APOC is not installed
        cypher_inter_doc_fallback = """
        UNWIND $records AS row
        MATCH (src:VanBan {id: toString(row.doc_id), lab_session: 'buoi_14'})
        MATCH (tgt:VanBan {id: toString(row.other_doc_id), lab_session: 'buoi_14'})
        FOREACH (ignore IN CASE WHEN row.relationship_type = 'SUA_DOI_BO_SUNG' THEN [1] ELSE [] END |
            MERGE (src)-[r:SUA_DOI_BO_SUNG {relationship: row.relationship, lab_session: 'buoi_14'}]->(tgt)
        )
        FOREACH (ignore IN CASE WHEN row.relationship_type = 'CAN_CU' THEN [1] ELSE [] END |
            MERGE (src)-[r:CAN_CU {relationship: row.relationship, lab_session: 'buoi_14'}]->(tgt)
        )
        FOREACH (ignore IN CASE WHEN row.relationship_type = 'VAN_BAN_BO_SUNG' THEN [1] ELSE [] END |
            MERGE (src)-[r:VAN_BAN_BO_SUNG {relationship: row.relationship, lab_session: 'buoi_14'}]->(tgt)
        )
        FOREACH (ignore IN CASE WHEN row.relationship_type = 'THAY_THE' THEN [1] ELSE [] END |
            MERGE (src)-[r:THAY_THE {relationship: row.relationship, lab_session: 'buoi_14'}]->(tgt)
        )
        FOREACH (ignore IN CASE WHEN row.relationship_type = 'HOP_NHAT' THEN [1] ELSE [] END |
            MERGE (src)-[r:HOP_NHAT {relationship: row.relationship, lab_session: 'buoi_14'}]->(tgt)
        )
        """
        try:
            session.run(cypher_inter_doc, records=rel_records)
        except Exception:
            session.run(cypher_inter_doc_fallback, records=rel_records)
            
        print(f"Loaded {len(rel_records)} legal relationships between VanBan nodes.")

        # Step 6: Audit and Statistics
        print("\n" + "="*60)
        print("AUDITING KNOWLEDGE GRAPH STATISTICS")
        print("="*60)
        
        # Node counts
        node_res = session.run("""
        MATCH (n {lab_session: 'buoi_14'})
        RETURN labels(n)[0] AS Label, count(n) AS Count ORDER BY Label
        """)
        node_stats = {r["Label"]: r["Count"] for r in node_res}
        print("Nodes by Label:", node_stats)
        
        # Relation counts
        rel_res = session.run("""
        MATCH ()-[r {lab_session: 'buoi_14'}]->()
        RETURN type(r) AS Type, count(r) AS Count ORDER BY Type
        """)
        rel_stats = {r["Type"]: r["Count"] for r in rel_res}
        print("Relationships by Type:", rel_stats)
        
        # Orphan nodes
        orphan_res = session.run("""
        MATCH (d:DieuKhoan {lab_session: 'buoi_14'})
        WHERE NOT (:VanBan)-[:CONTAINS]->(d)
        RETURN count(d) AS OrphanCount
        """)
        orphan_count = orphan_res.single()["OrphanCount"]
        print("Orphan DieuKhoan nodes:", orphan_count)
        print("="*60)

        # Step 7: Write kg_build_report.md
        with open(output_report, "w", encoding="utf-8") as f:
            f.write("# Báo Cáo Khởi Tạo Neo4j Mini Knowledge Graph (Buổi 14)\n\n")
            f.write(f"**Ngày thực hiện:** 15/08/2026  \n")
            f.write(f"**Neo4j Instance:** `{uri}` (Database: `{db}`)  \n")
            f.write(f"**Thẻ phân định dữ liệu (Tag):** `lab_session = 'buoi_14'`  \n")
            f.write(f"**Thư mục làm việc:** `/Users/lethilan/Downloads/Rag_thuchanh/graph_rag_labs/buoi_14`  \n\n")
            f.write("---\n\n")
            
            f.write("## 1. Thống Kê Node Theo Label\n\n")
            f.write("| Node Label | Số Lượng Node |\n")
            f.write("| :--- | :---: |\n")
            for lbl, cnt in node_stats.items():
                f.write(f"| `:{lbl}` | {cnt} |\n")
            f.write(f"| **Tổng cộng** | **{sum(node_stats.values())}** |\n\n")
            
            f.write("---\n\n")
            f.write("## 2. Thống Kê Quan Hệ (Relationships) Theo Type\n\n")
            f.write("| Relationship Type | Mô Tả / Nguồn | Số Lượng |\n")
            f.write("| :--- | :--- | :---: |\n")
            for rtype, cnt in rel_stats.items():
                desc = "Quan hệ chứa điều khoản" if rtype == "CONTAINS" else \
                       "Chuỗi thứ tự điều khoản" if rtype == "NEXT" else \
                       "Quan hệ pháp lý giữa các văn bản"
                f.write(f"| `:{rtype}` | {desc} | {cnt} |\n")
            f.write(f"| **Tổng cộng** | | **{sum(rel_stats.values())}** |\n\n")
            
            f.write("---\n\n")
            f.write("## 3. Kiểm Tra Node Mồ Côi (Orphan Nodes Check)\n\n")
            f.write(f"- **Số lượng Node `DieuKhoan` không liên kết với `VanBan` nào:** `{orphan_count}`\n")
            if orphan_count == 0:
                f.write("- **Đánh giá:** 100% các node `DieuKhoan` đều được liên kết chính xác về node `VanBan` chủ quản thông qua quan hệ `:CONTAINS`.\n\n")
            else:
                f.write(f"- **Cảnh báo:** Phát hiện `{orphan_count}` node bị mồ côi cần rà soát lại ID.\n\n")
                
            f.write("---\n\n")
            f.write("## 4. Kiểm Tra An Toàn Dữ Liệu Neo4j\n\n")
            f.write("- **Quy tắc làm sạch:** Chỉ thực hiện `DETACH DELETE` trên các node có thuộc tính `lab_session = 'buoi_14'`.\n")
            f.write("- **Không đụng chạm toàn bộ graph:** Không chạy `MATCH (n) DETACH DELETE n`, đảm bảo giữ nguyên vẹn dữ liệu của các buổi học khác.\n")
            f.write("- **Truy vấn tham số:** Tất cả các thao tác nạp dữ liệu đều sử dụng Parameterized Cypher (`$records`).\n")

        print(f"\nKnowledge Graph Report generated at: {output_report}")
        
    driver.close()

if __name__ == "__main__":
    load_mini_knowledge_graph()
