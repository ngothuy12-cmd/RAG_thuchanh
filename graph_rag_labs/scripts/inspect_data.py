import os
import pandas as pd
from pathlib import Path

def find_data_dir():
    # Search locations for data directory
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

def inspect():
    data_dir = find_data_dir()
    print("==================================================")
    print(" DATA INSPECTION REPORT (Wiki Risk Graph MVP)")
    print(f" Data directory found at: {data_dir.resolve()}")
    print("==================================================\n")

    files = {
        "risk_profiles_seed.csv": {
            "pk": "id",
            "fk": ["owner_unit_id"],
            "desc": "Hồ sơ Rủi ro (Node RuiRo)"
        },
        "controls_seed.csv": {
            "pk": "id",
            "fk": ["owner_role_id"],
            "desc": "Kiểm soát (Node KiemSoat)"
        },
        "risk_events_seed.csv": {
            "pk": "id",
            "fk": ["risk_id"],
            "desc": "Sự kiện Rủi ro (Node SuKienRuiRo)"
        },
        "relationships_seed.csv": {
            "pk": "(source_id, relationship_type, target_id)",
            "fk": ["source_id", "target_id"],
            "desc": "Quan hệ giữa các Node (Edges)"
        }
    }

    dfs = {}

    for fname, meta in files.items():
        fpath = data_dir / fname
        print(f"--- File: {fname} ({meta['desc']}) ---")
        if not fpath.exists():
            print(f"ERROR: File not found: {fpath}\n")
            continue
        
        df = pd.read_csv(fpath)
        dfs[fname] = df
        
        row_count = len(df)
        cols = list(df.columns)
        null_counts = df.isnull().sum().to_dict()
        total_nulls = df.isnull().sum().sum()
        
        if fname == "relationships_seed.csv":
            dup_rows = df.duplicated(subset=["source_id", "relationship_type", "target_id"]).sum()
        else:
            dup_rows = df.duplicated(subset=["id"]).sum()
        
        print(f"  • Số dòng (Rows count): {row_count}")
        print(f"  • Danh sách cột ({len(cols)}): {cols}")
        print(f"  • Khóa chính (Primary Key): {meta['pk']}")
        print(f"  • Khóa tham chiếu (Foreign Keys): {meta['fk']}")
        print(f"  • Tổng số giá trị Null: {total_nulls} {null_counts}")
        print(f"  • Số dòng trùng lặp (Duplicate rows): {dup_rows}")
        
        if fname == "relationships_seed.csv" and "relationship_type" in df.columns:
            rel_counts = df["relationship_type"].value_counts().to_dict()
            print(f"  • Các loại relationship_type: {rel_counts}")
        
        print()

    # Integrity & Reference checks
    print("==================================================")
    print(" KIỂM TRA THAM CHIẾU VÀ DỮ LIỆU THIẾU")
    print("==================================================")

    # Check relationships references
    if "relationships_seed.csv" in dfs:
        rel_df = dfs["relationships_seed.csv"]
        rp_ids = set(dfs["risk_profiles_seed.csv"]["id"]) if "risk_profiles_seed.csv" in dfs else set()
        ctrl_ids = set(dfs["controls_seed.csv"]["id"]) if "controls_seed.csv" in dfs else set()
        re_ids = set(dfs["risk_events_seed.csv"]["id"]) if "risk_events_seed.csv" in dfs else set()
        
        all_known_ids = rp_ids | ctrl_ids | re_ids
        
        missing_sources = set(rel_df["source_id"]) - all_known_ids
        missing_targets = set(rel_df["target_id"]) - all_known_ids
        
        print(f"  • Ref check relationships.source_id thiếu: {missing_sources if missing_sources else 'Không có (100% hợp lệ)'}")
        print(f"  • Ref check relationships.target_id thiếu: {missing_targets if missing_targets else 'Không có (100% hợp lệ)'}")

    if "risk_events_seed.csv" in dfs:
        re_df = dfs["risk_events_seed.csv"]
        rp_ids = set(dfs["risk_profiles_seed.csv"]["id"]) if "risk_profiles_seed.csv" in dfs else set()
        missing_risk_ids = set(re_df["risk_id"]) - rp_ids
        print(f"  • Ref check risk_events.risk_id thiếu: {missing_risk_ids if missing_risk_ids else 'Không có (100% hợp lệ)'}")

    # Detect Missing Master Data
    print("\n  [CẢNH BÁO DỮ LIỆU THAM CHIẾU CHƯA CÓ MASTER DATA]")
    if "risk_profiles_seed.csv" in dfs:
        units = set(dfs["risk_profiles_seed.csv"]["owner_unit_id"].dropna().unique())
        print(f"  • 'owner_unit_id' trong risk_profiles_seed.csv chứa {len(units)} mã đơn vị ({sorted(list(units))}), nhưng CHƯA CÓ bảng/file master data tương ứng cho Đơn vị (Unit).")
    if "controls_seed.csv" in dfs:
        roles = set(dfs["controls_seed.csv"]["owner_role_id"].dropna().unique())
        print(f"  • 'owner_role_id' trong controls_seed.csv chứa {len(roles)} mã vai trò ({sorted(list(roles))}), nhưng CHƯA CÓ bảng/file master data tương ứng cho Vai trò (Role).")

if __name__ == "__main__":
    inspect()
