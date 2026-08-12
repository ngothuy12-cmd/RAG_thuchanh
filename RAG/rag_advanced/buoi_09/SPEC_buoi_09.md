# Specification RAG Buổi 09: Hierarchical & Multi-Query

## 1. Mục tiêu và khác biệt Buổi 08/09
- **Mục tiêu**: Xây dựng kiến trúc Advanced RAG mở rộng, xử lý triệt để bài toán query routing/rewriting (Multi-query) và mất ngữ cảnh do chia nhỏ (Hierarchical Retrieval). 
- **Khác biệt**: 
  - Buổi 08 là Flat RAG (tìm và rerank trực tiếp các chunk đơn lẻ).
  - Buổi 09 áp dụng Query Expansion (Variants) kết hợp với Hierarchical Resolution (Child-to-Parent). Thay vì đưa các chunk lẻ tẻ cho LLM, hệ thống sẽ mở rộng query, sau đó tổng hợp các child hits để kéo toàn bộ context của Parent Document (thường là cấp Điều).

## 2. Sơ đồ kiến trúc (Workflow)
`Q0 (Original Query)` -> `LLM (Sinh N Variants)` -> `[Q0, Q1... Qn]` 
-> `Per-query Hybrid Retrieval (BM25 + Semantic)` 
-> `Cross-query RRF (Gộp kết quả các variants)` 
-> `Child-to-Parent Resolution (Ánh xạ chunk lên Parent)` 
-> `Parent Aggregation (Gộp điểm các Parent Candidate)` 
-> `Parent Rerank (Cross-encoder rerank toàn bộ Parent Document)` 
-> `Generation & Citation`.

## 3. Bốn mode thực thi
- `single_flat`: Chỉ dùng Q0, retrieval phẳng như Buổi 08 (Không mở rộng câu hỏi, không gộp Parent).
- `multi_flat`: Dùng Q0 + Variants, retrieval phẳng rồi RRF (Không gộp Parent).
- `single_parent`: Chỉ dùng Q0, retrieval phẳng sau đó resolution lên Parent.
- `multi_parent`: Đầy đủ pipeline Buổi 09 (Variants + RRF + Parent Resolution).

## 4. QueryVariant Schema và Validation
```python
class QueryVariant:
    variant_id: str
    text: str
    weight: float
```
- **Validation**: Số lượng variant <= MULTI_QUERY_COUNT. Độ dài mỗi variant <= MULTI_QUERY_MAX_CHARS. Nếu LLM sinh lỗi, fallback về mảng chỉ chứa Q0.

## 5. Hierarchy Registry Schema
- Là cấu trúc In-memory dictionary ánh xạ `parent_id` tới tập hợp các `child_ids` và `metadata`.
- Đảm bảo O(1) lookup từ child sang parent.

## 6. ParentDocument Schema
```python
class ParentDocument:
    parent_id: str
    text: str
    source: str
    children_ids: list[str]
    metadata: dict
```
- Text của Parent được nối từ toàn bộ children. Có giới hạn độ dài `PARENT_MAX_CHARS`.

## 7. MultiQueryChildHit và ParentCandidate Schema
- `MultiQueryChildHit`: Lưu vết chunk_id được match bởi query variant nào, rank bao nhiêu.
- `ParentCandidate`: Gồm `parent_id`, `aggregated_score`, danh sách `matched_children`, và text đầy đủ.

## 8. Quy tắc Hierarchy Resolution và Ambiguous Warning
- Mọi chunk (child) được tìm thấy phải được ánh xạ tới duy nhất 1 ParentDocument hợp lệ.
- **Ambiguous Warning**: Nếu metadata `article` bị thiếu (như ở phân tích Bước 01) nhưng chunk đó lại match với một Điều khác qua regex, hệ thống sẽ ném cảnh báo "Ambiguous Parent Resolution" nhưng vẫn ưu tiên metadata đã khai báo.

## 9. Công thức Cross-query RRF và Parent Aggregation
- **Cross-query RRF**: `Score(c) = sum(w_q / (k + rank(c, q)))` với `w_q` là weight của variant.
- **Parent Aggregation**: `ParentScore = sum(ChildScore)`. Có áp dụng giới hạn số lượng child đóng góp điểm (PARENT_SCORE_CHILD_LIMIT) để tránh bias cho các parent quá dài.

## 10. Context Budget và Citation Contract
- **Context Budget**: Tổng số lượng ký tự đưa vào Prompt (của tất cả ParentDocuments) không được vượt quá `TOTAL_CONTEXT_MAX_CHARS`. Nếu vượt, cắt bớt các Parent có rank thấp nhất.
- **Citation Contract**: LLM phải trích dẫn theo định dạng `[E1]`, `[E2]`. Trích dẫn trỏ về Parent Document thay vì các chunk nhỏ mồ côi.

## 11. Status/Failure Contract
- Mọi exception ở khâu tạo Variant hoặc Reranker model sẽ fallback hợp lý. Báo cáo rõ status (ví dụ: `variants_generation_failed`, `reranker_unavailable`, `success`).

## 12. Testability/Dependency Injection
- Các hàm sinh Variant hoặc hàm Rerank phải chấp nhận tham số (mock function) truyền vào để bypass việc gọi API/Model thật trong Unit Test.

## 13. Evaluation Metrics và Acceptance Criteria
- Cần đo lường MRR@K, Recall@K của `multi_parent` so với `single_flat`.
- **Acceptance Criteria**: Pipeline chạy qua không lỗi; Số lượng tokens cho context hợp lý; Trích dẫn đúng Parent.

## 14. Xác nhận
- Toàn bộ thay đổi và logic mới chỉ được phép ghi vào `rag_advanced/buoi_09/`. Không tác động hay sửa đổi bất kỳ code nào của Buổi 05 - Buổi 08.
