# RAG Foundation — Buổi 09: Multi-query & Parent–Child Retrieval

## 1. Mục tiêu và khác biệt so với Buổi 08
Dự án này là phiên bản nâng cấp hoàn chỉnh về Retrieval so với Buổi 08. 
- **Buổi 08**: Sử dụng mô hình tìm kiếm chunk đơn lẻ (Single-Query Flat Retrieval). Dễ dẫn đến việc nhặt các mảnh thông tin rời rạc, thiếu ngữ cảnh và không toàn vẹn về mặt pháp lý (Ví dụ: Trích dẫn Điều 8 nhưng thiếu phần đầu của Điều 8).
- **Buổi 09**: Khắc phục bằng kỹ thuật **Multi-query** (mở rộng câu hỏi) và **Parent-Child Retrieval** (Tìm kiếm qua các thẻ con, nhưng bốc toàn bộ thẻ cha). Giúp câu trả lời luôn bao hàm ngữ cảnh đầy đủ, bảo vệ tính toàn vẹn của văn bản pháp luật, đồng thời tăng diện bao phủ tìm kiếm bằng RRF.

## 2. Sơ đồ Pipeline Hai tầng Fusion và Parent Expansion
Pipeline diễn ra theo trình tự sau:
```
Query fan-out (Gemini Sinh Q0..Qn) 
  → Hybrid Search (BM25 + Semantic) cho TỪNG query (Inner RRF)
    → Hợp nhất kết quả bằng Cross-query RRF (Multi-Query RRF)
      → Map Child sang Parent (Child-to-Parent)
        → Parent Aggregation (Cộng điểm các Score Child, cắt Context Budget)
          → Rerank toàn văn Parent bằng Cross-encoder (Q0 + Parent)
            → Evidence Gating & Trả lời (Gemini)
```

## 3. Bốn Mode Comparison
- `single_flat`: Chỉ dùng câu hỏi gốc, trả về mảnh Child. Rerank Child. (Giống hệ thống Buổi 08).
- `multi_flat`: Dùng Multi-query Fan-out, tìm và hợp nhất Child. Rerank Child.
- `single_parent`: Dùng câu hỏi gốc, tìm Child nhưng mở rộng lên Parent. Rerank Parent.
- `multi_parent`: Đầy đủ tính năng. Multi-query, kéo lên Parent, Rerank Parent.

## 4. Cấu trúc Project và Setup `.env`
Các file chính nằm trong `rag_advanced/buoi_09/`:
- `hierarchical_rag.py`: Lõi xử lý Hierarchy, Multi-query và Parent-child.
- `evaluate.py`: Chạy evaluation offline và xuất report.
- `app.py`: Giao diện Streamlit.
- `ui_helpers.py`: Helper UI testable cho Streamlit.
- `.env`: File cấu hình biến môi trường (Ví dụ `GEMINI_API_KEY`, các trọng số weights...).

## 5. Build Hierarchy và Giải thích Warning/Ambiguous
Lệnh `hierarchy-build` quét dữ liệu từ Buổi 05 và tạo cấu trúc Parent (Article) - Child (Passage). 
- Nếu một thẻ Child pháp lý không thể tìm được Parent cha hợp lệ (do lỗi định dạng source), nó sẽ bị gắn nhãn **ambiguous**.
- Các Parent chứa ambiguous children sẽ sinh ra **Warning** chạy dọc xuống tận lúc Citation cho người dùng biết văn bản này có thể bị đứt gãy ngữ cảnh.

## 6. Query Expansion Contract và API Call Budget
- **Contract**: Q0 luôn là nguyên văn (bảo toàn). Các Variants (Q1..Qn) sinh ra từ LLM tập trung vào Paraphrase hoặc Missing Aspect.
- **Budget**: Mỗi truy vấn `multi_parent` tốn tối đa **2 lượt gọi Gemini Generation API** (1 mở rộng, 1 sinh câu trả lời) và nhiều lượt Embeddings API (phụ thuộc vào `MULTI_QUERY_COUNT`).

## 7. Công thức RRF
- **Inner RRF** (Per-query): Tích hợp trong `hybrid_search`, lai giữa Vector (Semantic) và Keyword (BM25).
- **Cross-query RRF**: Tổng của `Query Weight / (K + rank của child)`. Q0 thường có weight = 1.5, Variants = 1.0.
- **Parent Aggregation Score**: Tổng của `1 / (K + MQ-RRF Rank của Child)` (chỉ lấy top scoring children).

## 8. Child Retrieval, Parent Return, Rerank Parent
Thuật toán lấy top hits từ Child (bởi vì Child ngắn, embedding/BM25 chính xác hơn), nhưng thay vì trả Child, sẽ lookup Parent tương ứng và tải toàn văn Text của Parent. Cross-encoder reranker sau đó sẽ chấm điểm giữa câu hỏi gốc Q0 và khối Text Parent khổng lồ này để gate lại một lần cuối.

## 9. Các Lệnh Hỗ Trợ
- `hierarchy-audit` / `hierarchy-build` / `hierarchy-status`: Build và kiểm tra cấu trúc cha/con.
- `expand-query`: Chạy thử bộ sinh query.
- `multi-child`: Tìm Child bằng đa truy vấn.
- `parent-retrieve`: Tương tự multi-child nhưng mở rộng sang parent.
- `query`: Chạy toàn bộ pipeline (Có rerank và trả lời).
- `compare`: So sánh thông số 4 models không cần gen answers.
- `evaluate`: Tính MRR, Recall qua file questions.json.
- Chạy Streamlit: `python -m streamlit run rag_advanced/buoi_09/app.py`

## 10. Giải thích K và Context Budget
- `PER_QUERY_CANDIDATES`: Số Child tối đa lấy cho mỗi query.
- `PARENT_CANDIDATES`: Giới hạn số Parent trước khi đưa vào Reranker (Reranker rất nặng).
- `TOTAL_CONTEXT_MAX_CHARS`: Budget bảo vệ Context LLM. Nếu cắt bị lố, hệ thống chỉ bỏ Parent sau chứ không bao giờ cắt giữa chừng Parent để đảm bảo tính trọn vẹn.

## 11. Evaluation Metrics và Hạn Chế
File `evaluate.py` đo lường Child Recall@K, Parent Recall@K, MRR, nDCG, Latency.
**Lưu ý**: Nhãn đánh giá thủ công trong `questions.json` có thể chứa `needs_human_review=true`. Do đó, kết quả MRR cao trên mode Multi không đồng nghĩa thắng tuyệt đối, vì RAG pháp lý đôi khi cần con người đánh giá tính hợp lệ của lập luận chứ không chỉ text matching.

## 12. Troubleshooting
- **Hierarchy stale**: Báo lỗi `hierarchy_not_ready` khi `.env` đổi cấu hình token. Xử lý: chạy `hierarchy-build`.
- **Reranker/Latency**: Lần đầu tải model HuggingFace sẽ mất thời gian tải về ổ cứng và RAM. Nếu thiếu RAM, set `RERANK_DEVICE=cpu`.
- **Context lớn**: Nhận cảnh báo `first_parent_exceeds_budget` nghĩa là văn bản Luật này quá dài (VD: Luật Doanh nghiệp nguyên chương).

## 13. Tuyên bố Miễn Trừ
Đây là hệ thống tham khảo (Proof of Concept) kiến trúc RAG. Không đại diện cho các tư vấn pháp lý chính thức. Người dùng phải tham vấn luật sư hoặc tra cứu Cổng thông tin điện tử pháp điển trước khi ra quyết định kinh doanh hoặc pháp lý.
