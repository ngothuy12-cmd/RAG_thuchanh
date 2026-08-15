import os
import sys
import pandas as pd
from pathlib import Path

def load_env():
    env_vars = {}
    env_paths = [Path(".env"), Path("buoi_13/.env"), Path(__file__).parent.parent / ".env"]
    for ep in env_paths:
        if ep.exists():
            for line in ep.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip().strip("'\"")
            break
    return env_vars

def find_outputs_dir():
    candidates = [
        Path("outputs"),
        Path("buoi_13/outputs"),
        Path(__file__).parent / "outputs",
        Path(__file__).parent.parent / "outputs",
        Path(__file__).parent.parent / "buoi_13/outputs"
    ]
    for c in candidates:
        if c.exists() and c.is_dir() and (c / "entities.csv").exists():
            return c
    raise FileNotFoundError("Could not locate outputs directory containing entities.csv and relations.csv.")

def load_neo4j():
    print("==================================================")
    print(" NEO4J DATA LOADER (Wiki Risk Graph)")
    print("==================================================")

    # 1. Load .env config
    env = load_env()
    uri = os.getenv("NEO4J_URI", env.get("NEO4J_URI", "bolt://127.0.0.1:7687"))
    user = os.getenv("NEO4J_USER", os.getenv("NEO4J_USERNAME", env.get("NEO4J_USER", env.get("NEO4J_USERNAME", "neo4j"))))
    password = os.getenv("NEO4J_PASSWORD", env.get("NEO4J_PASSWORD", ""))
    database = os.getenv("NEO4J_DATABASE", env.get("NEO4J_DATABASE", "neo4j"))

    # 2. Check Python Neo4j Driver
    try:
        from neo4j import GraphDatabase, exceptions
    except ImportError:
        print("\n❌ CHƯA CÀI ĐẶT PYTHON NEO4J DRIVER!")
        print("  Vui lòng cài đặt bằng lệnh: pip install neo4j")
        print("  (Các bước chuẩn hóa dữ liệu và sinh Wiki Markdown trước đó vẫn hoàn toàn hợp lệ!)\n")
        return

    if not password:
        print("\n❌ THIẾU CẤU HÌNH NEO4J_PASSWORD TRONG FILE .env!")
        print("  Vui lòng bổ sung NEO4J_PASSWORD vào file .env.\n")
        return

    # 3. Test Neo4j Connection
    print(f" Connecting to Neo4j at {uri} (User: {user}, Database: {database})...")
    driver = None
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        print("  --> Kết nối Neo4j thành công!")
    except Exception as e:
        print("\n⚠️ KHÔNG THỂ KẾT NỐI TỚI NEO4J SERVER!")
        print(f"  Lỗi kết nối: {e}")
        print("\n💡 HƯỚNG DẪN KHẮC PHỤC:")
        print("  1. Hãy đảm bảo ứng dụng Neo4j Desktop hoặc Docker container Neo4j đang bật.")
        print("  2. Lệnh khởi chạy Neo4j bằng Docker mẫu:")
        print(f"     docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH={user}/{password} neo4j:latest")
        print("  3. (Lưu ý: Không làm ảnh hưởng tới kết quả sinh Wiki Markdown trước đó).\n")
        if driver:
            driver.close()
        return

    # 4. Read outputs/entities.csv & outputs/relations.csv
    try:
        outputs_dir = find_outputs_dir()
        df_entities = pd.read_csv(outputs_dir / "entities.csv").fillna("")
        df_relations = pd.read_csv(outputs_dir / "relations.csv").fillna("")
    except Exception as e:
        print(f"\n❌ LỖI ĐỌC FILE OUTPUTS: {e}")
        driver.close()
        return

    # 5. Load Schema Constraints & Data into Neo4j
    with driver.session(database=database) as session:
        print("\n--- 1. Tạo Unique Constraints cho Nodes ---")
        constraints = [
            "CREATE CONSTRAINT constraint_ruiro_id IF NOT EXISTS FOR (r:RuiRo) REQUIRE r.id IS UNIQUE;",
            "CREATE CONSTRAINT constraint_kiemsoat_id IF NOT EXISTS FOR (k:KiemSoat) REQUIRE k.id IS UNIQUE;",
            "CREATE CONSTRAINT constraint_sukienruiro_id IF NOT EXISTS FOR (s:SuKienRuiRo) REQUIRE s.id IS UNIQUE;"
        ]
        for c in constraints:
            try:
                session.run(c)
            except Exception as e:
                print(f"  Warning constraint: {e}")
        print("  --> Constraints updated!")

        print("\n--- 2. Nạp Nodes (MERGE) ---")
        loaded_nodes = 0
        for _, row in df_entities.iterrows():
            eid = row["id"]
            etype = row["type"]
            
            # Clean row dict
            props = {k: v for k, v in row.to_dict().items() if v != ""}
            
            cypher = f"MERGE (n:{etype} {{id: $id}}) SET n += $props"
            session.run(cypher, id=eid, props=props)
            loaded_nodes += 1
        print(f"  --> Đã nạp thành công {loaded_nodes} Nodes vào Neo4j!")

        print("\n--- 3. Nạp Edges (MERGE) ---")
        loaded_edges = 0
        for _, row in df_relations.iterrows():
            sid = row["source_id"]
            tid = row["target_id"]
            rtype = row["relationship_type"]
            
            props = row.to_dict()
            
            if rtype == "MITIGATES":
                cypher = """
                MATCH (s:KiemSoat {id: $source_id}), (t:RuiRo {id: $target_id})
                MERGE (s)-[r:MITIGATES]->(t)
                SET r += $props
                """
            elif rtype == "OBSERVED_AS":
                cypher = """
                MATCH (s:RuiRo {id: $source_id}), (t:SuKienRuiRo {id: $target_id})
                MERGE (s)-[r:OBSERVED_AS]->(t)
                SET r += $props
                """
            else:
                continue

            session.run(cypher, source_id=sid, target_id=tid, props=props)
            loaded_edges += 1
        print(f"  --> Đã nạp thành công {loaded_edges} Edges vào Neo4j!")

    driver.close()
    print("\n==================================================")
    print(" KẾT QUẢ: NẠP DỮ LIỆU VÀO NEO4J HOÀN TẤT VÀ HỢP LỆ!")
    print("==================================================")

if __name__ == "__main__":
    load_neo4j()
