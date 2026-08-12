# Agent Specification - Buổi 07

## Workspace
- Vùng được đọc: `rag_foundation/buoi_05/output/chunks/`, `rag_foundation/buoi_05/.venv/`, `rag_foundation/buoi_06/`, `rag_foundation/buoi_07/`
- Vùng được ghi: `rag_foundation/buoi_07/`
- Tuyệt đối không sửa Buổi 05 và Buổi 06.

## Python
- Dùng `.venv` của Buổi 05.
- Không tạo venv mới.

## Input
- JSON trong `buoi_05/output/chunks/`.
- Buổi 05 là nguồn dữ liệu đã chuẩn bị.
- Không thực hiện OCR, parse PDF hoặc chunk lại.

## Packages
- Chỉ dùng package được quy định trong `requirements.txt`.

## Pipeline
- Validate dữ liệu đầu vào.
- Embedding.
- Chroma persistent.
- Retrieval.
- Confidence gate.
- Generation.
- Citation.
- Streamlit.
- Unittest offline.

## Data Contract
Các field bắt buộc:
- chunk_id
- strategy
- source
- page_start
- page_end
- text

## Index Contract
- Một strategy trong một collection.
- Model và dimension của index/query phải khớp.
- Dùng embedding thật, không dùng vector giả.
- Chặn NaN, Infinity, boolean và zero vector.
- Dùng khoảng cách Chroma cosine, `embedding_function=None`.
- Đảm bảo tính Idempotent.
- Status read-only.
- Validate embedding xong trước khi reset/upsert.

## Retrieval Contract
- Trả evidence thật.
- Có distance đi kèm.
- Chỉ đưa evidence đạt threshold vào generation.
- Evidence yếu thì không gọi generation.

## Citation Contract
- Citation lấy từ metadata thật.
- Không tin source/page/chunk_id do LLM tự tạo.
- Kết quả (result) có `citations` và `warnings`; code thay thế label hợp lệ bằng citation thật.

## Security
- Không làm lộ secret.

## Testing
- Unittest.
- Mock API.
- Temporary storage.
- Không gọi Internet/key thật trong test.

## Coding Style
- Ít file.
- Ít class.
- Ít function.
- Không sử dụng kiến trúc phức tạp.
