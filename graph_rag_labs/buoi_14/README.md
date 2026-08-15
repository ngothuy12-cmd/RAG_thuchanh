# BUỔI 14 — Nâng cấp RAG với Hybrid Search + Reranking và xây Knowledge Graph mini

Thư mục này chứa toàn bộ tài nguyên, kịch bản xử lý, dữ liệu đầu ra và mã nguồn thực thi riêng cho **Buổi 14**.

---

## 1. Cấu trúc thư mục `buoi_14/`

```text
buoi_14/
├── .venv/                      # Môi trường ảo Python riêng cho Buổi 14
├── app.py                      # Giao diện Web Demo Streamlit
├── cache/                      # Thư mục cache vector embeddings cho Dense Retrieval
├── cypher/
│   ├── schema.cypher           # Định nghĩa Ràng buộc Unique & Index trên Neo4j
│   └── demo_queries.cypher     # Các truy vấn Cypher mẫu kiểm tra Knowledge Graph
├── src/
│   ├── __init__.py
│   ├── bm25_retriever.py       # Module BM25 Retrieval
│   ├── dense_retriever.py      # Module Dense Retrieval (Vietnamese Bi-Encoder)
│   ├── hybrid_retriever.py     # Module Hybrid Search (Reciprocal Rank Fusion - RRF)
│   ├── reranker.py             # Module CrossEncoder Reranking (mmarco-mMiniLMv2)
│   └── unified_retriever.py    # Module Unified Retrieval với hàm retrieve() thống nhất
├── scripts/
│   ├── prepare_corpus.py       # Kịch bản chuẩn hóa corpus
│   ├── baseline_retrieval.py   # CLI demo chạy & so sánh BM25 vs Dense
│   ├── hybrid_search.py        # CLI demo chạy Hybrid Search (RRF)
│   ├── rerank.py               # CLI demo chạy Hybrid Search + CrossEncoder Reranking
│   ├── compare_retrieval.py    # Kịch bản đánh giá Benchmark 4 cấu hình Retrieval
│   ├── load_mini_kg.py         # Kịch bản khởi tạo & nạp Mini Knowledge Graph vào Neo4j
│   └── query_demo.py           # CLI demo hàm retrieve() thống nhất kèm GRAPH HINTS
├── data/
│   ├── eval/
│   │   └── questions.csv       # Tập câu hỏi kiểm thử Gold Set (9 câu: Keyword, Semantic, Mixed)
│   └── processed/
│       └── chunks_normalized.csv # Bộ dữ liệu 791 chunks đã chuẩn hóa
└── outputs/
    ├── inspection_report.md    # Báo cáo kiểm tra tiền đề
    ├── retrieval_examples.md   # Báo cáo kết quả thử nghiệm ví dụ qua 4 tầng Retrieval
    ├── retrieval_comparison.csv # Kết quả đánh giá chi tiết theo từng câu hỏi
    ├── evaluation_report.md    # Báo cáo đánh giá Benchmark tổng quan
    └── kg_build_report.md      # Báo cáo khởi tạo Neo4j Mini Knowledge Graph
```

---

## 2. Dữ liệu đầu vào

Dữ liệu được đọc trực tiếp từ thư mục gốc `../kb+hops/` (nguyên vẹn, không chỉnh sửa/ghi đè):
- `../kb+hops/metadata.csv`: Thông tin metadata và trích dẫn văn bản (15 văn bản).
- `../kb+hops/content.csv`: Nội dung HTML đầy đủ của các văn bản.
- `../kb+hops/relationships.csv`: Các mối quan hệ pháp lý giữa các văn bản.

---

## 3. Hướng dẫn chạy chuẩn hóa Corpus

```bash
cd /Users/lethilan/Downloads/Rag_thuchanh/graph_rag_labs/buoi_14
source .venv/bin/activate
python scripts/prepare_corpus.py
```

---

## 4. Hướng dẫn chạy Baseline Retrieval (BM25 vs Dense)

```bash
python scripts/baseline_retrieval.py --query "Quy định về giao nhận tiền mặt theo Thông tư 01/2014/TT-NHNN" --top-k 5
```

---

## 5. Hướng dẫn chạy Hybrid Search (Reciprocal Rank Fusion - RRF)

```bash
python scripts/hybrid_search.py --query "Quy định về giao nhận tiền mặt theo Thông tư 01/2014/TT-NHNN" --candidate-k 20 --top-k 5
```

---

## 6. Hướng dẫn chạy Pipeline Hoàn Chỉnh (Hybrid Search + CrossEncoder Reranking)

```bash
python scripts/rerank.py --query "Theo Nghị định 73/2016/NĐ-CP thì điều kiện cấp giấy phép hoạt động doanh nghiệp bảo hiểm gồm những gì?" --candidate-k 20 --top-k 5
```

---

## 7. Hướng dẫn chạy Đánh Giá Benchmark (Evaluation Framework)

```bash
python scripts/compare_retrieval.py
```

---

## 8. Hướng dẫn Nạp Neo4j Mini Knowledge Graph

```bash
python scripts/load_mini_kg.py
```

---

## 9. Hướng dẫn Chạy Giao Diện Web Demo Streamlit (`app.py`)

### A. Lệnh chạy Streamlit Server:
```bash
cd /Users/lethilan/Downloads/Rag_thuchanh/graph_rag_labs/buoi_14
source .venv/bin/activate

streamlit run app.py
```
*Giao diện Web sẽ tự động mở hoặc truy cập tại URL:* `http://localhost:8503` (hoặc `http://localhost:8501`).

### B. Cách dừng Streamlit Server:
- Nhấn tổ hợp phím **`Ctrl + C`** trong cửa sổ terminal đang chạy server Streamlit.

### C. Cách chọn phương pháp Retrieval (Method Selection):
Tại cột điều khiển bên trái (Sidebar):
- **BM25:** Tìm kiếm khớp từ khóa chính xác (mã số hiệu, số điều).
- **Dense:** Vector search bằng Bi-Encoder tiếng Việt (`bkai-foundation-models/vietnamese-bi-encoder`).
- **Hybrid:** Hợp nhất BM25 + Dense bằng Reciprocal Rank Fusion (RRF).
- **Hybrid + Rerank:** Tái xếp hạng các candidates bằng mô hình CrossEncoder (`mmarco-mMiniLMv2`).

### D. Giải thích các trường kết quả hiển thị:
- **`Rank`**: Thứ hạng của chunk trong danh sách kết quả trả về.
- **`Score`**: Điểm số tương ứng tùy thuộc phương pháp (BM25 score, Cosine similarity, RRF score, hoặc CrossEncoder relevance score).
- **`Citation`**: Trích dẫn nguồn (Tên văn bản / Số hiệu, Điều khoản và `chunk_id`) phục vụ kiểm tra nguồn gốc.
- **`Text`**: Đoạn văn bản nội dung đầy đủ của chunk.
- **`BEFORE vs AFTER RERANK`**: Bảng đối chiếu thứ hạng của candidate trước (ở RRF) và sau khi được CrossEncoder tái sắp xếp.
- **`Graph Hints`**: Xuất thông tin 1-hop các quan hệ pháp lý giữa các văn bản (`SUA_DOI_BO_SUNG`, `CAN_CU`, `THAY_THE`, v.v.) và chuỗi `NEXT` điều khoản kế cận từ Neo4j.
