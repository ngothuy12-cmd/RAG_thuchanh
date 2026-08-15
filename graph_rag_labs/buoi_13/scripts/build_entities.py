import os
import pandas as pd
from pathlib import Path

def find_data_dir():
    candidates = [
        Path("data"),
        Path("buoi_13/data"),
        Path(__file__).parent / "data",
        Path(__file__).parent.parent / "data",
        Path(__file__).parent.parent / "buoi_13/data"
    ]
    for c in candidates:
        if c.exists() and c.is_dir() and (c / "risk_profiles_seed.csv").exists():
            return c
    raise FileNotFoundError("Could not locate data directory containing seed CSV files.")

def get_output_dirs(data_dir: Path):
    out1 = data_dir.parent / "outputs"
    out1.mkdir(parents=True, exist_ok=True)
    
    out2 = Path("outputs")
    out2.mkdir(parents=True, exist_ok=True)
    return [out1, out2]

def build():
    data_dir = find_data_dir()
    output_dirs = get_output_dirs(data_dir)
    
    # 1. Read seed CSVs
    rp_path = data_dir / "risk_profiles_seed.csv"
    ctrl_path = data_dir / "controls_seed.csv"
    re_path = data_dir / "risk_events_seed.csv"
    rel_path = data_dir / "relationships_seed.csv"

    df_rp = pd.read_csv(rp_path)
    df_ctrl = pd.read_csv(ctrl_path)
    df_re = pd.read_csv(re_path)
    df_rel = pd.read_csv(rel_path)

    # 2. Build entities dataframe
    entities_list = []

    # Map risk_profiles_seed.csv -> RuiRo
    for _, row in df_rp.iterrows():
        entities_list.append({
            "id": row["id"],
            "type": "RuiRo",
            "name": row["name"],
            "description": row["description"],
            "source_file": "risk_profiles_seed.csv",
            "data_origin": row["data_origin"],
            "verification_status": row["verification_status"],
            "category": row.get("category", ""),
            "cause": row.get("cause", ""),
            "event": row.get("event", ""),
            "impact": row.get("impact", ""),
            "inherent_level": row.get("inherent_level", ""),
            "residual_level": row.get("residual_level", ""),
            "owner_unit_id": row.get("owner_unit_id", ""),
            "control_type": "",
            "frequency": "",
            "owner_role_id": "",
            "effectiveness": "",
            "risk_id": "",
            "occurred_at": "",
            "discovered_at": "",
            "severity": "",
            "loss_amount_vnd": ""
        })

    # Map controls_seed.csv -> KiemSoat
    for _, row in df_ctrl.iterrows():
        entities_list.append({
            "id": row["id"],
            "type": "KiemSoat",
            "name": row["name"],
            "description": row.get("description", ""),
            "source_file": "controls_seed.csv",
            "data_origin": row["data_origin"],
            "verification_status": row["verification_status"],
            "category": "",
            "cause": "",
            "event": "",
            "impact": "",
            "inherent_level": "",
            "residual_level": "",
            "owner_unit_id": "",
            "control_type": row.get("control_type", ""),
            "frequency": row.get("frequency", ""),
            "owner_role_id": row.get("owner_role_id", ""),
            "effectiveness": row.get("effectiveness", ""),
            "risk_id": "",
            "occurred_at": "",
            "discovered_at": "",
            "severity": "",
            "loss_amount_vnd": ""
        })

    # Map risk_events_seed.csv -> SuKienRuiRo
    for _, row in df_re.iterrows():
        entities_list.append({
            "id": row["id"],
            "type": "SuKienRuiRo",
            "name": row["description"],
            "description": row["description"],
            "source_file": "risk_events_seed.csv",
            "data_origin": row["data_origin"],
            "verification_status": row["verification_status"],
            "category": "",
            "cause": "",
            "event": "",
            "impact": "",
            "inherent_level": "",
            "residual_level": "",
            "owner_unit_id": "",
            "control_type": "",
            "frequency": "",
            "owner_role_id": "",
            "effectiveness": "",
            "risk_id": row.get("risk_id", ""),
            "occurred_at": row.get("occurred_at", ""),
            "discovered_at": row.get("discovered_at", ""),
            "severity": row.get("severity", ""),
            "loss_amount_vnd": row.get("loss_amount_vnd", "")
        })

    df_entities = pd.DataFrame(entities_list)

    # 3. Build relations dataframe from relationships_seed.csv
    rel_cols = [
        "source_id", "relationship_type", "target_id", 
        "source", "evidence_quote", "confidence", 
        "verification_status", "data_origin"
    ]
    df_relations = df_rel[rel_cols].copy()

    # Save to outputs
    for out_dir in set(output_dirs):
        df_entities.to_csv(out_dir / "entities.csv", index=False)
        df_relations.to_csv(out_dir / "relations.csv", index=False)
        print(f" Saved entities.csv and relations.csv to: {out_dir.resolve()}")

    # 4. Validation & Statistics
    print("\n==================================================")
    print(" KẾT QUẢ CHUẨN HÓA DỮ LIỆU (BUILD SUMMARY)")
    print("==================================================")

    # Statistics for entities by type
    print("\n--- THỐNG KÊ ENTITIES THEO TYPE ---")
    type_counts = df_entities["type"].value_counts().to_dict()
    total_entities = len(df_entities)
    for etype in ["RuiRo", "KiemSoat", "SuKienRuiRo"]:
        count = type_counts.get(etype, 0)
        print(f"  • {etype}: {count} entities")
    print(f"  --> Tổng số Entities: {total_entities}")

    # Statistics for relations by relationship_type
    print("\n--- THỐNG KÊ RELATIONS THEO RELATIONSHIP_TYPE ---")
    rel_type_counts = df_relations["relationship_type"].value_counts().to_dict()
    total_relations = len(df_relations)
    for rtype in ["MITIGATES", "OBSERVED_AS"]:
        count = rel_type_counts.get(rtype, 0)
        print(f"  • {rtype}: {count} relations")
    print(f"  --> Tổng số Relations: {total_relations}")

    # 5. Check for orphan references
    print("\n--- KIỂM TRA ORPHAN REFERENCE ---")
    all_entity_ids = set(df_entities["id"])
    
    orphan_sources = []
    orphan_targets = []
    
    for idx, row in df_relations.iterrows():
        sid = row["source_id"]
        tid = row["target_id"]
        if sid not in all_entity_ids:
            orphan_sources.append((idx, sid, row["relationship_type"]))
        if tid not in all_entity_ids:
            orphan_targets.append((idx, tid, row["relationship_type"]))

    has_error = False
    if orphan_sources:
        print(f"  [LỖI] Phát hiện {len(orphan_sources)} orphan source_id trong relations.csv: {orphan_sources}")
        has_error = True
    else:
        print("  • source_id: 100% hợp lệ, tồn tại trong entities.csv")

    if orphan_targets:
        print(f"  [LỖI] Phát hiện {len(orphan_targets)} orphan target_id trong relations.csv: {orphan_targets}")
        has_error = True
    else:
        print("  • target_id: 100% hợp lệ, tồn tại trong entities.csv")

    if not has_error:
        print("  --> KHÔNG CÓ LỖI ORPHAN REFERENCE! Dữ liệu đạt chuẩn tích hợp graph.")

if __name__ == "__main__":
    build()
