import os
import sys
import json
import pandas as pd
from neo4j import GraphDatabase

# Add buoi_14 directory to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
buoi14_dir = os.path.dirname(script_dir)
if buoi14_dir not in sys.path:
    sys.path.insert(0, buoi14_dir)

from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE


def load_secure_knowledge_graph():
    input_file = os.path.join(buoi14_dir, "data", "processed", "chunks_secure.csv")
    
    print(f"Reading security tagged dataset from: {input_file}")
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Missing tagged dataset file: {input_file}. Please run assign_security_tags.py first.")

    df = pd.read_csv(input_file).fillna("")
    print(f"Loaded {len(df)} records from {os.path.basename(input_file)}.")

    # Prepare payload records for Cypher batch execution
    records = []
    for _, row in df.iterrows():
        try:
            roles_list = json.loads(row["allowed_roles"]) if isinstance(row["allowed_roles"], str) else row["allowed_roles"]
        except Exception:
            roles_list = ["Admin", "HR", "Risk_Manager", "Staff", "Guest"]
            
        records.append({
            "chunk_id": str(row["chunk_id"]),
            "document_id": str(row["document_id"]),
            "allowed_roles": roles_list
        })

    print(f"Connecting to Neo4j database at {NEO4J_URI} (DB: {NEO4J_DATABASE})...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session(database=NEO4J_DATABASE) as session:
        # Step 1: Update DieuKhoan nodes with allowed_roles (List of Strings)
        print("Updating 'allowed_roles' property on DieuKhoan nodes...")
        cypher_update_dieukhoan = """
        UNWIND $records AS row
        MERGE (d:DieuKhoan {id: row.chunk_id})
        SET d.allowed_roles = row.allowed_roles,
            d.document_id = row.document_id,
            d.lab_session = 'buoi_15'
        """
        session.run(cypher_update_dieukhoan, records=records)
        print("✔ Successfully updated allowed_roles on DieuKhoan nodes.")

        # Step 2: Ensure CONTAINS relationships exist between VanBan and DieuKhoan
        print("Ensuring CONTAINS relationships between VanBan and DieuKhoan nodes...")
        cypher_link_vanban = """
        UNWIND $records AS row
        MERGE (v:VanBan {id: row.document_id})
        ON CREATE SET v.lab_session = 'buoi_15'
        WITH v, row
        MATCH (d:DieuKhoan {id: row.chunk_id})
        MERGE (v)-[r:CONTAINS]->(d)
        ON CREATE SET r.lab_session = 'buoi_15'
        """
        session.run(cypher_link_vanban, records=records)
        print("✔ CONTAINS relationships verified/updated.")

        # Step 3: Aggregate allowed_roles onto VanBan nodes
        print("Aggregating document-level 'allowed_roles' on VanBan nodes...")
        cypher_update_vanban = """
        MATCH (v:VanBan)-[:CONTAINS]->(d:DieuKhoan)
        UNWIND d.allowed_roles AS role
        WITH v, collect(DISTINCT role) AS unique_roles
        SET v.allowed_roles = unique_roles,
            v.lab_session = 'buoi_15'
        """
        session.run(cypher_update_vanban)
        print("✔ Successfully aggregated allowed_roles on VanBan nodes.")

        # ==============================================================================
        # POST-LOADING VERIFICATION & AUDIT
        # ==============================================================================
        print("\n" + "=" * 70)
        print("NEO4J SECURE GRAPH AUDIT REPORT")
        print("=" * 70)

        # 1. Count nodes with allowed_roles
        count_dieukhoan = session.run(
            "MATCH (d:DieuKhoan) WHERE d.allowed_roles IS NOT NULL RETURN count(d) AS count"
        ).single()["count"]
        
        count_vanban = session.run(
            "MATCH (v:VanBan) WHERE v.allowed_roles IS NOT NULL RETURN count(v) AS count"
        ).single()["count"]

        total_dieukhoan = session.run("MATCH (d:DieuKhoan) RETURN count(d) AS count").single()["count"]
        total_vanban = session.run("MATCH (v:VanBan) RETURN count(v) AS count").single()["count"]

        print(f"• DieuKhoan Nodes tagged with allowed_roles : {count_dieukhoan}/{total_dieukhoan}")
        print(f"• VanBan Nodes tagged with allowed_roles    : {count_vanban}/{total_vanban}")

        # 2. Sample 1 VanBan node and its child DieuKhoan nodes
        print("\n--- SAMPLE VANBAN AND CONNECTED DIEUKHOAN NODES ---")
        sample_query = """
        MATCH (v:VanBan)-[:CONTAINS]->(d:DieuKhoan)
        WHERE v.allowed_roles IS NOT NULL
        RETURN v.id AS vanban_id, 
               v.so_ky_hieu AS so_ky_hieu,
               v.title AS title, 
               v.allowed_roles AS vanban_roles,
               collect({
                   id: d.id, 
                   article: d.article, 
                   allowed_roles: d.allowed_roles
               })[0..3] AS sample_dieukhoans
        LIMIT 1
        """
        sample_res = session.run(sample_query).single()

        if sample_res:
            print(f"📌 VanBan Node ID        : {sample_res['vanban_id']}")
            print(f"   • Title               : {sample_res['title']}")
            print(f"   • Số ký hiệu          : {sample_res['so_ky_hieu']}")
            print(f"   • VanBan allowed_roles: {sample_res['vanban_roles']} (Type: {type(sample_res['vanban_roles']).__name__})")
            print("\n   📌 Child DieuKhoan Nodes Sample:")
            for d in sample_res['sample_dieukhoans']:
                print(f"      - DieuKhoan ID: {d['id']:<20} | Roles: {d['allowed_roles']}")
        else:
            print("⚠️ No sample VanBan found!")

        print("\n" + "=" * 70)
        print("Neo4j Secure Graph update completed successfully.")

    driver.close()

if __name__ == "__main__":
    load_secure_knowledge_graph()
