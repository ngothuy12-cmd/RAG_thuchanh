# Specification - Buổi 08 (Advanced RAG)

## 1. Workspace và security
- Dự án được đặt trong thư mục `rag_advanced/buoi_08/`.
- File `.env` chứa thông tin nhạy cảm và không được push lên version control.
- Toàn bộ storage và reports được lưu trữ cục bộ trong dự án Buổi 08, cô lập hoàn toàn với các buổi khác.

## 2. Quan hệ với Buổi 05 và Buổi 07
- Dữ liệu chunking được kế thừa từ Buổi 05 (`hierarchical`, `semantic`, `fixed-size`).
- Pipeline baseline semantic RAG được kế thừa từ Buổi 07 qua bản sao của `rag.py`. Buổi 08 không trực tiếp import code hay sử dụng runtime storage của Buổi 07 để đảm bảo tính cô lập và khả năng kiểm thử độc lập.

## 3. Data contract
- Dữ liệu input là mảng JSON chứa các chunk đã được chuẩn hóa.
- Mỗi chunk tối thiểu bao gồm: `chunk_id`, `strategy`, `source`, `page_start`, `page_end`, `text`.

## 4. BM25 tokenizer/retrieval contract
- Bộ tokenizer BM25 phải xử lý tiếng Việt hiệu quả (có thể dùng underthesea hoặc các thư viện tách từ chuẩn tiếng Việt).
- Trả về danh sách các ứng viên dựa trên độ khớp từ khóa (lexical search).
- Kết quả từ BM25 phải trả về dưới dạng danh sách kèm score.

## 5. Semantic candidate contract
- Lấy ứng viên dựa trên Semantic Embeddings (như đã triển khai ở Buổi 07).
- Hỗ trợ mô hình embedding đa ngôn ngữ hoặc mô hình đặc tả tiếng Việt.
- Kết quả từ Semantic Search phải trả về danh sách ứng viên kèm khoảng cách (distance) hoặc độ tương đồng (similarity).

## 6. RRF fusion contract
- Áp dụng Reciprocal Rank Fusion (RRF) để kết hợp kết quả xếp hạng từ BM25 (Lexical) và Semantic Search.
- Thuật toán RRF: `Score = 1 / (k + rank)`, trong đó `k` thường bằng 60.
- Output là một danh sách hợp nhất đã được tái xếp hạng từ 2 nguồn retriever.

## 7. Cross-encoder reranker contract
- Đưa danh sách hợp nhất từ RRF qua Cross-encoder model để rerank lần cuối.
- Input: `(Query, Chunk Text)`.
- Output: Relevance score có độ chính xác cao.
- Chọn Top K cuối cùng (thường là 3-5 chunks) đưa vào LLM context.

## 8. Final evidence và citation contract
- Chỉ các chunk vượt qua bước reranking và thỏa mãn một độ tin cậy nhất định mới được coi là evidence.
- Trích dẫn (citation) bắt buộc phải chèn đúng `chunk_id`, `source`, `page_start`, `page_end` vào câu trả lời, không tự ý bịa thêm nguồn.

## 9. Pipeline trace contract
- Quá trình pipeline (BM25 score, Semantic dist, RRF rank, Reranker score) phải được trace và có thể output ra debug log nhằm phục vụ giám sát và kiểm thử.
- Cấu trúc trace rõ ràng (thời gian, input, output từng khâu).

## 10. Evaluation metrics contract
- Offline eval đánh giá thông qua các metric: Precision@K, Recall@K, MRR (Mean Reciprocal Rank), và Hit Rate.
- Sử dụng dataset trong thư mục `eval/` có gán nhãn gold labels (`needs_human_review=true`).

## 11. Offline testing contract
- Chạy đánh giá batch qua `evaluate.py`.
- Kết quả phải ghi nhận vào thư mục `reports/` dưới dạng JSON/CSV/Markdown báo cáo chi tiết theo từng query.

## 12. UI comparison contract
- `app.py` triển khai giao diện so sánh side-by-side (hoặc tab) giữa kết quả Baseline (chỉ dùng Semantic) và kết quả Advanced RAG (BM25 + Semantic + RRF + Reranker).
- Hiển thị trực quan quá trình truy xuất, bao gồm score và rank.
