# Advanced RAG (Buổi 08)

## 1. Mục tiêu và khác biệt Buổi 07 / 08
Dự án này là phiên bản nâng cấp hoàn thiện của Buổi 07.
- **Buổi 07**: Chỉ dùng Vector Search (Semantic) bằng Gemini Embedding và Chroma.
- **Buổi 08**: Nâng cấp lên **Advanced RAG** bằng sự kết hợp của:
  - Lexical Search (BM25)
  - Semantic Search (Chroma)
  - Reciprocal Rank Fusion (RRF)
  - Cross-encoder Reranking (BGE-Reranker-v2-m3)

## 2. Sơ đồ Pipeline
`Query -> [BM25 Search] & [Semantic Search] -> [RRF Fusion] -> [Cross-encoder Reranker] -> [Gating] -> LLM Answer`

## 3. Cấu trúc project
Chỉ tập trung trong thư mục `rag_advanced/buoi_08/`:
- `advanced_rag.py`: Lõi xử lý (BM25, Hybrid, Reranker, Query Pipeline).
- `rag.py`: Các hàm foundation public tái sử dụng.
- `app.py`: Giao diện UI đa tầng trên Streamlit.
- `evaluate.py`: Công cụ đo lường metrics (Recall, MRR, nDCG).
- `tests/`: Bộ Unit test toàn vẹn (mock offline).

## 4. Setup
1. Môi trường: Dùng chung `.venv` của `rag_foundation/buoi_05`. 
2. Dependencies: `pip install -r requirements.txt`.
3. `.env`: Bạn copy `.env.example` sang `.env` và điền `GEMINI_API_KEY`. (Không có key sẽ fail chứ không dùng vector giả).

## 5. Cảnh báo Reranker
- Model `BAAI/bge-reranker-v2-m3` được lazy-load khi gọi mode `hybrid_rerank`.
- Ở lần tải đầu tiên, sẽ cần Internet và ngốn khoảng 2GB ổ cứng (trong thư mục `storage/huggingface/`) và RAM để load.

## 6. Lệnh Command CLI
Đứng ở gốc Workspace (`RAG`):
- Xem trạng thái: `python rag_advanced/buoi_08/advanced_rag.py status`
- Nạp Index (Semantic): `python rag_advanced/buoi_08/advanced_rag.py prepare-semantic`
- Chẩn đoán BM25: `python rag_advanced/buoi_08/advanced_rag.py bm25 --question "..."`
- Chẩn đoán Hybrid: `python rag_advanced/buoi_08/advanced_rag.py hybrid --question "..."`
- Chẩn đoán Rerank: `python rag_advanced/buoi_08/advanced_rag.py rerank --question "..."`
- So sánh 4 modes: `python rag_advanced/buoi_08/advanced_rag.py compare --question "..."`
- Tạo câu trả lời: `python rag_advanced/buoi_08/advanced_rag.py query --mode hybrid_rerank --question "..."`

## 7. Lệnh Test, Eval và Streamlit
- Unittest: `python -m unittest discover rag_advanced/buoi_08/tests`
- Evaluate: `python rag_advanced/buoi_08/evaluate.py --k 5`
- Giao diện UI: `python -m streamlit run rag_advanced/buoi_08/app.py`

## 8. Giải thích Metric Scores
- **BM25 score**: Điểm exact match, cao hơn là tốt hơn (không chuẩn hóa).
- **Cosine distance**: Điểm khoảng cách góc, thấp hơn là tốt hơn (0-2).
- **RRF score**: Điểm hợp nhất lai theo công thức `1/(k+rank)`. Cao hơn là tốt hơn.
- **Rerank score**: Sigmoid của logit, thuộc [0,1]. Cao hơn là tốt hơn. (Lưu ý: Không phải là xác suất đúng tuyệt đối).

## 9. Candidate K và Final K
- `BM25_CANDIDATES` & `SEMANTIC_CANDIDATES`: Số chunk lấy thô từ mỗi nhánh.
- `RERANK_CANDIDATES`: Lấy Top N sau khi RRF để đưa qua mô hình nặng (Reranker).
- `FINAL_TOP_K`: Số lượng evidence tối đa nhồi vào Prompt cho Generation.

## 10. Evaluation Metrics
Hỗ trợ `Recall@K`, `MRR@K`, `nDCG@K` với binary relevance.
Gold labels trong `eval/questions.json` có `needs_human_review`. Chừng nào cờ này bật, báo cáo không kết luận Mode chiến thắng tuyệt đối.

## 11. Troubleshooting
- Lỗi API Rate Limit (Gemini 429): Script `rag.py` đã cấu hình auto retry/sleep. Cần kiên nhẫn treo máy.
- Reranker thiếu RAM hoặc CPU chậm: Hãy dùng `RERANK_DEVICE=cpu` và kiên nhẫn.
- Model chưa được tải: Nếu bị lỗi timeout khi download huggingface, bạn cần mở command `rerank` thủ công 1 lần để máy tải xong.

## 12. Khước từ trách nhiệm
*Dự án này là minh họa kỹ thuật Advanced RAG trên văn bản pháp luật, hoàn toàn **KHÔNG PHẢI TƯ VẤN PHÁP LÝ**.*
