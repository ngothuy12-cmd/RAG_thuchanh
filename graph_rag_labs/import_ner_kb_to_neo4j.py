import os
import sys
import pandas as pd
from pathlib import Path
from neo4j import GraphDatabase

def load_env():
    env_vars = {}
    env_paths = [Path(".env"), Path(__file__).parent / ".env"]
    for ep in env_paths:
        if ep.exists():
            for line in ep.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip().strip("'\"")
            break
    return env_vars

def main():
    print("==================================================")
    print(" BUỔI 12 - NEO4J KNOWLEDGE GRAPH IMPORT & VERIFY")
    print("==================================================")

    # 1. Load config from .env
    env = load_env()
    uri = os.getenv("NEO4J_URI", env.get("NEO4J_URI", "bolt://127.0.0.1:7687"))
    user = os.getenv("NEO4J_USER", os.getenv("NEO4J_USERNAME", env.get("NEO4J_USER", env.get("NEO4J_USERNAME", "neo4j"))))
    password = os.getenv("NEO4J_PASSWORD", env.get("NEO4J_PASSWORD", "abcd1234"))
    database = os.getenv("NEO4J_DATABASE", env.get("NEO4J_DATABASE", "neo4j"))

    print(f"📡 Kết nối tới Neo4j tại {uri} (User: {user}, Database: {database})...")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        print("✅ Kết nối Neo4j thành công!")
    except Exception as e:
        print(f"❌ Lỗi kết nối Neo4j: {e}")
        sys.exit(1)

    # 2. Đọc file dữ liệu từ ner_kb
    ner_kb_dir = Path(__file__).parent / "ner_kb"
    file_docs = ner_kb_dir / "cleaned_documents.csv"
    file_entities = ner_kb_dir / "entities.csv"
    file_rel = ner_kb_dir / "relationships.csv"

    if not (file_docs.exists() and file_entities.exists() and file_rel.exists()):
        print("❌ Thiếu file dữ liệu trong thư mục ner_kb!")
        driver.close()
        sys.exit(1)

    df_docs = pd.read_csv(file_docs).fillna("")
    df_entities = pd.read_csv(file_entities).fillna("")
    df_rel = pd.read_csv(file_rel).fillna("")

    print(f"📄 Đã tải: {len(df_docs)} Document, {len(df_entities)} Entity, {len(df_rel)} Relationship.")

    with driver.session(database=database) as session:
        # 3. Tạo Uniqueness Constraints
        print("\n⚙️ 1. Khởi tạo Constraints...")
        constraints = [
            "CREATE CONSTRAINT constraint_doc_symbol IF NOT EXISTS FOR (d:Document) REQUIRE d.so_ky_hieu IS UNIQUE;",
            "CREATE CONSTRAINT constraint_coquan_name IF NOT EXISTS FOR (c:CoQuan) REQUIRE c.name IS UNIQUE;",
            "CREATE CONSTRAINT constraint_nguoiky_name IF NOT EXISTS FOR (p:NguoiKy) REQUIRE p.name IS UNIQUE;",
            "CREATE CONSTRAINT constraint_doituong_name IF NOT EXISTS FOR (o:DoiTuongApDung) REQUIRE o.name IS UNIQUE;",
            "CREATE CONSTRAINT constraint_linhvuc_name IF NOT EXISTS FOR (l:LinhVuc) REQUIRE l.name IS UNIQUE;"
        ]
        for c in constraints:
            try:
                session.run(c)
            except Exception as e:
                print(f"  ⚠️ Warning constraint: {e}")
        print("✅ Constraints đã sẵn sàng.")

        # 4. Import Document Nodes
        print("\n📥 2. MERGE Document Nodes...")
        query_doc = """
        UNWIND $rows AS row
        MERGE (d:Document {so_ky_hieu: row.so_ky_hieu})
        SET d.id = row.id,
            d.title = row.title,
            d.ngay_ban_hanh = row.ngay_ban_hanh,
            d.loai_van_ban = row.loai_van_ban,
            d.co_quan_ban_hanh = row.co_quan_ban_hanh,
            d.nguoi_ky = row.nguoi_ky,
            d.linh_vuc = row.linh_vuc,
            d.pham_vi = row.pham_vi,
            d.tinh_trang_hieu_luc = row.tinh_trang_hieu_luc
        """
        session.run(query_doc, rows=df_docs.to_dict('records'))
        print(f"✅ MERGE xong {len(df_docs)} Document nodes.")

        # 5. Import Entity Nodes (CoQuan, NguoiKy, DoiTuongApDung, LinhVuc)
        print("\n📥 3. MERGE Entity Nodes...")
        entity_queries = {
            'CoQuan': "UNWIND $rows AS row MERGE (n:CoQuan {name: row.canonical_name})",
            'NguoiKy': "UNWIND $rows AS row MERGE (n:NguoiKy {name: row.canonical_name})",
            'DoiTuongApDung': "UNWIND $rows AS row MERGE (n:DoiTuongApDung {name: row.canonical_name})",
            'LinhVuc': "UNWIND $rows AS row MERGE (n:LinhVuc {name: row.canonical_name})"
        }
        for etype, q in entity_queries.items():
            sub_df = df_entities[df_entities['entity_type'] == etype]
            if not sub_df.empty:
                session.run(q, rows=sub_df.to_dict('records'))
                print(f"  -> {etype}: MERGE {len(sub_df)} nodes.")

        # 6. Import Relationships
        print("\n📥 4. MERGE Relationships...")
        rel_errors = 0
        for idx, row in df_rel.iterrows():
            src = row['source']
            tgt = row['target']
            rtype = row['relationship_type']
            
            if rtype == 'BAN_HANH_BOI':
                q_rel = """
                MATCH (d:Document {so_ky_hieu: $src})
                MATCH (e:CoQuan {name: $tgt})
                MERGE (d)-[:BAN_HANH_BOI]->(e)
                """
            elif rtype == 'KY_BOI':
                q_rel = """
                MATCH (d:Document {so_ky_hieu: $src})
                MATCH (e:NguoiKy {name: $tgt})
                MERGE (d)-[:KY_BOI]->(e)
                """
            elif rtype == 'AP_DUNG_CHO':
                q_rel = """
                MATCH (d:Document {so_ky_hieu: $src})
                MATCH (e:DoiTuongApDung {name: $tgt})
                MERGE (d)-[:AP_DUNG_CHO]->(e)
                """
            elif rtype == 'THUOC_LINH_VUC':
                q_rel = """
                MATCH (d:Document {so_ky_hieu: $src})
                MATCH (e:LinhVuc {name: $tgt})
                MERGE (d)-[:THUOC_LINH_VUC]->(e)
                """
            elif rtype in ['THAM_CHIEU', 'SUA_DOI_BO_SUNG', 'THAY_THE_BOI']:
                q_rel = f"""
                MATCH (d1:Document {{so_ky_hieu: $src}})
                MATCH (d2:Document {{so_ky_hieu: $tgt}})
                MERGE (d1)-[:{rtype}]->(d2)
                """
            else:
                rel_errors += 1
                continue
                
            res = session.run(q_rel, src=src, tgt=tgt)
        
        print(f"✅ MERGE xong {len(df_rel)} Relationships (Lỗi: {rel_errors}).")

        # 7. Verification Queries (BƯỚC 9)
        print("\n📊 5. Báo cáo Thống kê Đồ thị Tri thức Neo4j (BƯỚC 9):")
        
        # Node statistics
        res_nodes = session.run("""
        MATCH (n)
        RETURN labels(n)[0] AS label, count(*) AS total
        ORDER BY total DESC
        """)
        print("\n--- 📌 Thống kê Nodes theo Label ---")
        for r in res_nodes:
            print(f"  - {r['label']}: {r['total']} nodes")
            
        # Relationship statistics
        res_rels = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) AS rel_type, count(*) AS total
        ORDER BY total DESC
        """)
        print("\n--- 🔗 Thống kê Relationships theo Type ---")
        for r in res_rels:
            print(f"  - {r['rel_type']}: {r['total']} relationships")
            
        # Sample document chain
        res_chain = session.run("""
        MATCH path=(a:Document)-[:THAM_CHIEU|SUA_DOI_BO_SUNG|THAY_THE_BOI]->(b:Document)
        RETURN a.so_ky_hieu AS src, type(relationships(path)[0]) AS rel, b.so_ky_hieu AS tgt
        LIMIT 5
        """)
        print("\n--- 🔍 Mẫu chuỗi quan hệ Document -> Document ---")
        for r in res_chain:
            print(f"  - {r['src']} -[:{r['rel']}]-> {r['tgt']}")

    driver.close()
    print("\n🎉 HOÀN THÀNH KẾT NỐI VÀ IMPORT BUỔI 12 VÀO NEO4J SUCCESSFUL!")

if __name__ == "__main__":
    main()
