# 🛡️ Wiki Risk Graph Project

Hệ thống xây dựng **Wiki Tri Thức Rủi Ro Dạng Đồ Thị (Wiki Risk Graph)** phục vụ đào tạo và quản trị rủi ro ngân hàng.

---

## 🏗️ Kiến Trúc Hệ Thống (System Pipeline)

```text
[ Seed CSVs ]
  data/risk_profiles_seed.csv
  data/controls_seed.csv
  data/risk_events_seed.csv
  data/relationships_seed.csv
        │
        ▼  (python3 scripts/inspect_data.py)
[ Báo Cáo Kiểm Tra Dữ Liệu Gốc ]
        │
        ▼  (python3 scripts/build_entities.py)
[ Chuẩn Hóa Dữ Liệu Entities & Relations ]
  outputs/entities.csv
  outputs/relations.csv
        │
        ├──► (python3 scripts/build_wiki.py)
        │    ▼
        │   [ Wiki Markdown Pages ] (Dành cho Obsidian Graph View)
        │     wiki/Home.md
        │     wiki/risks/*.md
        │     wiki/controls/*.md
        │     wiki/events/*.md
        │
        ├──► (python3 scripts/validate_wiki.py)
        │    ▼
        │   [ Báo Cáo Kiểm Thử Wiki ]
        │     outputs/wiki_validation_report.md
        │
        └──► (python3 scripts/load_neo4j.py)
             ▼
            [ Neo4j Knowledge Graph Database ]
              cypher/schema.cypher
              cypher/demo_queries.cypher
```

---

## 🚀 Thứ Tự Lệnh Chạy Project (Step-by-Step Execution Sequence)

Để vận hành toàn bộ quy trình xây dựng Wiki Risk Graph từ dữ liệu thô đến Obsidian Wiki và Neo4j, hãy chạy các lệnh theo đúng thứ tự sau:

### Bước 1: Kiểm Tra Dữ Liệu Seed Gốc
```bash
python3 scripts/inspect_data.py
```
* **Mục tiêu**: Đọc 4 file CSV seed, kiểm tra số dòng, tên cột, khóa chính, khóa ngoại, trùng lặp, null và phát hiện master data còn thiếu.

### Bước 2: Chuẩn Hóa Dữ Liệu Thành Entities & Relations
```bash
python3 scripts/build_entities.py
```
* **Mục tiêu**: Đọc 4 file CSV seed và chuẩn hóa thành 2 bảng dữ liệu chính:
  - `outputs/entities.csv` (Thực thể `RuiRo`, `KiemSoat`, `SuKienRuiRo`).
  - `outputs/relations.csv` (Quan hệ `MITIGATES`, `OBSERVED_AS`).

### Bước 3: Sinh Trang Wiki Markdown Cho Obsidian
```bash
python3 scripts/build_wiki.py
```
* **Mục tiêu**: Tự động sinh trang `wiki/Home.md` và các trang Markdown trong `wiki/risks/`, `wiki/controls/`, `wiki/events/` với các liên kết Obsidian Wikilink `[[Note Name]]`.

### Bước 4: Kiểm Thử Tự Động Chất Lượng Wiki
```bash
python3 scripts/validate_wiki.py
```
* **Mục tiêu**: Chạy 9 bài kiểm thử đối soát tính hợp lệ của trang Wiki, wikilinks, broken links, orphan pages và xuất báo cáo kết quả ra `outputs/wiki_validation_report.md`.

### Bước 5: Nạp Dữ Liệu Vào Neo4j Database (Tùy chọn)
```bash
python3 scripts/load_neo4j.py
```
* **Mục tiêu**: Đọc cấu hình từ `.env` (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`) và nạp dữ liệu Nodes/Edges vào CSDL đồ thị Neo4j bằng câu lệnh `MERGE` parameterized Cypher.

---

## 📂 Cấu Trúc File & Thư Mục Project

* **`data/`**: Chứa 4 file CSV seed dữ liệu rủi ro gốc.
* **`outputs/`**: Chứa bảng chuẩn hóa `entities.csv`, `relations.csv` và báo cáo `wiki_validation_report.md`.
* **`wiki/`**: Thư mục Wiki Vault dành cho Obsidian (`Home.md`, `risks/`, `controls/`, `events/`).
* **`cypher/`**:
  * `schema.cypher`: Các câu lệnh định nghĩa Unique Constraint cho Neo4j.
  * `demo_queries.cypher`: 6 mẫu truy vấn Cypher demo phục vụ tra cứu đồ thị.
* **`scripts/`**:
  * `inspect_data.py`: Script kiểm tra dữ liệu seed gốc.
  * `build_entities.py`: Script chuẩn hóa dữ liệu thành `entities.csv` và `relations.csv`.
  * `build_wiki.py`: Script sinh hệ thống Wiki Markdown.
  * `validate_wiki.py`: Script kiểm thử tự động hệ thống Wiki.
  * `load_neo4j.py`: Script nạp dữ liệu vào Neo4j Database.

---

## 🔍 Cypher Demo Queries Mẫu Trong Neo4j

Các câu truy vấn Cypher mẫu đã được chuẩn bị tại [`cypher/demo_queries.cypher`](file:///Users/lethilan/Downloads/Rag_thuchanh/graph_rag_labs/cypher/demo_queries.cypher):

1. **Xem toàn bộ graph**:
   ```cypher
   MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m;
   ```
2. **Tìm kiểm soát giảm thiểu rủi ro**:
   ```cypher
   MATCH (c:KiemSoat)-[r:MITIGATES]->(rr:RuiRo {id: 'RR-001'}) RETURN c, r, rr;
   ```
3. **Tìm sự kiện rủi ro**:
   ```cypher
   MATCH (rr:RuiRo {id: 'RR-001'})-[r:OBSERVED_AS]->(e:SuKienRuiRo) RETURN rr, r, e;
   ```
4. **Tìm đường liên kết 3 chặng**:
   ```cypher
   MATCH path = (c:KiemSoat)-[:MITIGATES]->(rr:RuiRo)-[:OBSERVED_AS]->(e:SuKienRuiRo) RETURN path;
   ```
5. **Tìm rủi ro chưa có kiểm soát**:
   ```cypher
   MATCH (rr:RuiRo) WHERE NOT (:KiemSoat)-[:MITIGATES]->(rr) RETURN rr;
   ```
6. **Tìm quan hệ chưa VERIFIED**:
   ```cypher
   MATCH (a)-[r]->(b) WHERE r.verification_status <> 'VERIFIED' RETURN r;
   ```
