import os
import pandas as pd
from pathlib import Path

def find_inputs_dir():
    candidates = [
        Path("outputs"),
        Path("buoi_13/outputs"),
        Path(__file__).parent / "outputs",
        Path(__file__).parent.parent / "outputs",
        Path(__file__).parent.parent / "buoi_13/outputs"
    ]
    for c in candidates:
        if c.exists() and c.is_dir() and (c / "entities.csv").exists() and (c / "relations.csv").exists():
            return c
    raise FileNotFoundError("Could not locate outputs directory containing entities.csv and relations.csv.")

def get_wiki_dirs(input_dir: Path):
    dirs = []
    w1 = input_dir.parent / "wiki"
    dirs.append(w1)
    w2 = Path("wiki")
    dirs.append(w2)
    
    unique_dirs = list(set(dirs))
    for d in unique_dirs:
        (d / "risks").mkdir(parents=True, exist_ok=True)
        (d / "controls").mkdir(parents=True, exist_ok=True)
        (d / "events").mkdir(parents=True, exist_ok=True)
    return unique_dirs

def sanitize_filename(name):
    if not isinstance(name, str):
        name = str(name)
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    res = name
    for c in invalid_chars:
        res = res.replace(c, '_')
    return res.strip()

def format_loss(val):
    try:
        if val == "" or pd.isna(val):
            return "0 VNĐ"
        return f"{float(val):,.0f} VNĐ"
    except Exception:
        return f"{val} VNĐ"

def build_wiki():
    input_dir = find_inputs_dir()
    wiki_dirs = get_wiki_dirs(input_dir)

    df_entities = pd.read_csv(input_dir / "entities.csv").fillna("")
    df_relations = pd.read_csv(input_dir / "relations.csv").fillna("")

    entities_by_id = {}
    title_by_id = {}

    for _, row in df_entities.iterrows():
        eid = row["id"]
        ename = row["name"]
        
        if ename and ename != eid:
            title = f"{eid} - {ename}"
        else:
            title = f"{eid}"
        
        title_sanitized = sanitize_filename(title)
        title_by_id[eid] = title_sanitized
        entities_by_id[eid] = row.to_dict()

    outbound_rel = {}
    inbound_rel = {}

    for _, row in df_relations.iterrows():
        sid = row["source_id"]
        tid = row["target_id"]
        rdict = row.to_dict()
        
        outbound_rel.setdefault(sid, []).append(rdict)
        inbound_rel.setdefault(tid, []).append(rdict)

    last_wikilink_count = 0
    pages_created_count = 0

    for wdir in wiki_dirs:
        wikilink_count = 0
        
        def make_wikilink(target_id, rel_type, evidence, status):
            nonlocal wikilink_count
            wikilink_count += 1
            target_title = title_by_id.get(target_id, target_id)
            evidence_str = f' | Bằng chứng: "{evidence}"' if evidence else ''
            return f"- [[{target_title}]] *(Quan hệ: `{rel_type}` | Trạng thái: `{status}`{evidence_str})*"

        # 1. Risks (RuiRo)
        for _, row in df_entities[df_entities["type"] == "RuiRo"].iterrows():
            eid = row["id"]
            title = title_by_id[eid]
            fpath = wdir / "risks" / f"{title}.md"
            
            ctrl_links = []
            for r in inbound_rel.get(eid, []):
                if r["relationship_type"] == "MITIGATES":
                    ctrl_links.append(make_wikilink(r["source_id"], r["relationship_type"], r.get("evidence_quote", ""), r.get("verification_status", "")))
            
            event_links = []
            for r in outbound_rel.get(eid, []):
                if r["relationship_type"] == "OBSERVED_AS":
                    event_links.append(make_wikilink(r["target_id"], r["relationship_type"], r.get("evidence_quote", ""), r.get("verification_status", "")))

            ctrl_section = "\n".join(ctrl_links) if ctrl_links else "*Không có kiểm soát liên quan*"
            event_section = "\n".join(event_links) if event_links else "*Không có sự kiện liên quan*"

            content = f"""---
id: {row['id']}
type: {row['type']}
verification_status: {row['verification_status']}
data_origin: {row['data_origin']}
---

# {title}

## 📋 Thông tin Hồ sơ Rủi ro
- **Mã rủi ro**: `{row['id']}`
- **Tên rủi ro**: {row['name']}
- **Danh mục (Category)**: {row['category']}
- **Mức độ rủi ro tiềm tàng (Inherent Level)**: `{row['inherent_level']}`
- **Mức độ rủi ro còn lại (Residual Level)**: `{row['residual_level']}`
- **Đơn vị phụ trách (Owner Unit ID)**: `{row['owner_unit_id']}`

## 📝 Mô tả Chi tiết
{row['description']}

### 🎯 Nguyên nhân, Sự kiện & Hậu quả
- **Nguyên nhân (Cause)**: {row['cause']}
- **Sự kiện (Event)**: {row['event']}
- **Tác động / Hậu quả (Impact)**: {row['impact']}

---

## 🛡️ Các Kiểm soát Giảm thiểu (Controls - MITIGATES)
{ctrl_section}

---

## 💥 Các Sự kiện Rủi ro Thực tế (Events - OBSERVED_AS)
{event_section}
"""
            fpath.write_text(content, encoding="utf-8")

        # 2. Controls (KiemSoat)
        for _, row in df_entities[df_entities["type"] == "KiemSoat"].iterrows():
            eid = row["id"]
            title = title_by_id[eid]
            fpath = wdir / "controls" / f"{title}.md"
            
            risk_links = []
            for r in outbound_rel.get(eid, []):
                if r["relationship_type"] == "MITIGATES":
                    risk_links.append(make_wikilink(r["target_id"], r["relationship_type"], r.get("evidence_quote", ""), r.get("verification_status", "")))

            risk_section = "\n".join(risk_links) if risk_links else "*Không có rủi ro liên quan*"

            content = f"""---
id: {row['id']}
type: {row['type']}
verification_status: {row['verification_status']}
data_origin: {row['data_origin']}
---

# {title}

## 🛡️ Thông tin Biện pháp Kiểm soát
- **Mã kiểm soát**: `{row['id']}`
- **Tên kiểm soát**: {row['name']}
- **Loại kiểm soát (Control Type)**: `{row['control_type']}`
- **Tần suất thực hiện (Frequency)**: {row['frequency']}
- **Hiệu quả (Effectiveness)**: `{row['effectiveness']}`
- **Vai trò phụ trách (Owner Role ID)**: `{row['owner_role_id']}`

---

## 🎯 Rủi ro Giảm thiểu (Mitigated Risks)
{risk_section}
"""
            fpath.write_text(content, encoding="utf-8")

        # 3. Events (SuKienRuiRo)
        for _, row in df_entities[df_entities["type"] == "SuKienRuiRo"].iterrows():
            eid = row["id"]
            title = title_by_id[eid]
            fpath = wdir / "events" / f"{title}.md"
            
            risk_links = []
            for r in inbound_rel.get(eid, []):
                if r["relationship_type"] == "OBSERVED_AS":
                    risk_links.append(make_wikilink(r["source_id"], r["relationship_type"], r.get("evidence_quote", ""), r.get("verification_status", "")))

            risk_section = "\n".join(risk_links) if risk_links else "*Không có rủi ro liên quan*"
            loss_str = format_loss(row['loss_amount_vnd'])

            content = f"""---
id: {row['id']}
type: {row['type']}
verification_status: {row['verification_status']}
data_origin: {row['data_origin']}
---

# {title}

## 💥 Thông tin Sự kiện Rủi ro
- **Mã sự kiện**: `{row['id']}`
- **Thời gian xảy ra**: `{row['occurred_at']}`
- **Thời gian phát hiện**: `{row['discovered_at']}`
- **Mức độ nghiêm trọng (Severity)**: `{row['severity']}`
- **Tổn thất tài chính**: `{loss_str}`

## 📝 Mô tả Sự kiện
{row['description']}

---

## 🔗 Rủi ro Nguyên nhân (Observed Risk)
{risk_section}
"""
            fpath.write_text(content, encoding="utf-8")

        # 4. Home.md
        home_path = wdir / "Home.md"
        
        risk_list_md = []
        for _, r in df_entities[df_entities["type"] == "RuiRo"].iterrows():
            t = title_by_id[r["id"]]
            wikilink_count += 1
            risk_list_md.append(f"- [[{t}]] - *{r['category']}* (`{r['inherent_level']}`)")

        ctrl_list_md = []
        for _, c in df_entities[df_entities["type"] == "KiemSoat"].iterrows():
            t = title_by_id[c["id"]]
            wikilink_count += 1
            ctrl_list_md.append(f"- [[{t}]] - *{c['control_type']}* (`{c['effectiveness']}`)")

        event_list_md = []
        for _, e in df_entities[df_entities["type"] == "SuKienRuiRo"].iterrows():
            t = title_by_id[e["id"]]
            wikilink_count += 1
            event_list_md.append(f"- [[{t}]] - *Mức độ `{e['severity']}`*")

        home_content = f"""---
id: HOME
type: Dashboard
verification_status: VERIFIED
data_origin: SYSTEM
---

# 🏠 Wiki Risk Graph - Trang Chủ Tra Cứu Rủi Ro

Chào mừng bạn đến với **Wiki Risk Graph**, hệ thống tri thức rủi ro dạng đồ thị liên kết.

---

## 📊 Thống Kê Tổng Quan Đồ Thị
- **Tổng số Nodes (Thực thể)**: `{len(df_entities)}`
  - 📋 **Hồ sơ Rủi ro (`RuiRo`)**: `{len(df_entities[df_entities['type'] == 'RuiRo'])}` nodes
  - 🛡️ **Kiểm soát (`KiemSoat`)**: `{len(df_entities[df_entities['type'] == 'KiemSoat'])}` nodes
  - 💥 **Sự kiện Rủi ro (`SuKienRuiRo`)**: `{len(df_entities[df_entities['type'] == 'SuKienRuiRo'])}` nodes
- **Tổng số Edges (Quan hệ)**: `{len(df_relations)}`
  - 🛡️ ➡️ 📋 **Giảm thiểu (`MITIGATES`)**: `{len(df_relations[df_relations['relationship_type'] == 'MITIGATES'])}` edges
  - 📋 ➡️ 💥 **Biểu hiện (`OBSERVED_AS`)**: `{len(df_relations[df_relations['relationship_type'] == 'OBSERVED_AS'])}` edges

---

## 🔗 Danh Mục Liên Kết Nhanh

### 📋 Danh Sách Hồ Sơ Rủi Ro (`risks/`)
{chr(10).join(risk_list_md)}

---

### 🛡️ Danh Sách Biện Pháp Kiểm Soát (`controls/`)
{chr(10).join(ctrl_list_md)}

---

### 💥 Danh Sách Sự Kiện Rủi Ro (`events/`)
{chr(10).join(event_list_md)}
"""
        home_path.write_text(home_content, encoding="utf-8")
        last_wikilink_count = wikilink_count
        print(f" Generated Wiki at: {wdir.resolve()}")

    total_pages = len(df_entities) + 1
    
    ks_example = title_by_id.get("KS-001", "KS-001")
    rr_example = title_by_id.get("RR-001", "RR-001")
    sk_example = title_by_id.get("SK-001", "SK-001")

    print("\n==================================================")
    print(" KẾT QUẢ SINH WIKI MARKDOWN (BUILD WIKI SUMMARY)")
    print("==================================================")
    print(f"  • Số trang Wiki đã tạo: {total_pages} trang (Home.md + {len(df_entities[df_entities['type'] == 'RuiRo'])} risks + {len(df_entities[df_entities['type'] == 'KiemSoat'])} controls + {len(df_entities[df_entities['type'] == 'SuKienRuiRo'])} events)")
    print(f"  • Tổng số wikilink Obsidian đã tạo: {last_wikilink_count} wikilinks")
    print(f"  • Ví dụ đường đi liên kết 3 chặng (Path Example):")
    print(f"    [[{ks_example}]]")
    print(f"        └─[:MITIGATES]─> [[{rr_example}]]")
    print(f"                             └─[:OBSERVED_AS]─> [[{sk_example}]]")

if __name__ == "__main__":
    build_wiki()
