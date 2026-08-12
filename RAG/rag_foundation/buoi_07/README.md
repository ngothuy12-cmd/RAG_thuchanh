# RAG Pipeline Buổi 07

## 1. Mục tiêu
Dự án này là phiên bản hoàn thiện của Pipeline Retrieval-Augmented Generation (RAG) nâng cao, được xây dựng dựa trên dữ liệu đã tiền xử lý từ các buổi trước. Mục tiêu chính là cung cấp giao diện tương tác Streamlit thân thiện để người dùng thực hiện Lập chỉ mục (Index) và Truy vấn (Query) dựa trên văn bản pháp lý.

## 2. Quan hệ với Buổi 05 và Buổi 06
- **Buổi 05**: Nơi chứa dữ liệu thô và các Chunk đã được cắt gọt, lưu tại `rag_foundation/buoi_05/output/chunks/`.
- **Buổi 06**: Tiền đề về kiến trúc RAG nâng cao, tuy nhiên ở Buổi 07, chúng ta kết nối trực tiếp với Storage của ChromaDB cục bộ và ứng dụng vào app giao diện (UI) mà không làm hỏng cấu trúc hiện tại.

## 3. Sơ đồ pipeline
```text
[Data JSON Buổi 05] -> [Validate & Lọc theo Strategy] -> [Gemini Embedding] -> [ChromaDB Indexing]
                                                                                      |
[User Query qua UI] -> [Gemini Query Embedding] ---------------------------------------
                               |
                               v
                       [Cosine Distance Retrieval] -> [Confidence Gate (Max Distance)]
                               |
                               v
[Lọc Evidence Đạt] -> [Prompt Injection & Grounding] -> [Gemini Generation] -> [Citation Mapping] -> [Hiển thị Giao diện]
```

## 4. Cấu trúc thư mục
```text
rag_foundation/buoi_07/
├── .env.example        # Mẫu file cấu hình môi trường
├── .env                # File cấu hình (không push lên git)
├── .gitignore          # Chặn commit .env và storage
├── app.py              # Giao diện UI viết bằng Streamlit
├── rag.py              # Mã nguồn lõi xử lý RAG logic
├── requirements.txt    # Danh sách thư viện Python
├── README.md           # Hướng dẫn sử dụng
├── storage/            # Thư mục chứa ChromaDB data
│   └── chroma/         # Vector persistent storage
└── tests/
    └── test_rag.py     # Bộ Unit Test tự động (Offline Mock)
```

## 5. Điều kiện đầu vào
- Máy đã cài đặt Python.
- Đã chạy thành công Buổi 05 và có sẵn thư mục `output/chunks/` chứa dữ liệu JSON.
- Đã chuẩn bị sẵn API Key của Google Gemini.

## 6. Cách dùng `.venv` Buổi 05
Thay vì tạo mới môi trường ảo, chúng ta tái sử dụng `.venv` của Buổi 05 để tiết kiệm dung lượng.
- **Windows**: `rag_foundation/buoi_05/.venv/Scripts/python.exe`
- **Linux/macOS**: `rag_foundation/buoi_05/.venv/bin/python`

## 7. Cách cài requirements
Sử dụng môi trường ảo của Buổi 05 để cài bổ sung:
```bash
<python-path> -m pip install -r rag_foundation/buoi_07/requirements.txt
```

## 8. Cách tạo `.env` từ `.env.example`
Mở Terminal, sao chép file cấu hình mẫu:
```bash
cp rag_foundation/buoi_07/.env.example rag_foundation/buoi_07/.env
```
Mở file `.env` vừa tạo và điền `GEMINI_API_KEY` của bạn vào.

## 9. Giải thích từng biến môi trường
- `GEMINI_API_KEY`: Khóa bảo mật để gọi API Google GenAI.
- `GEMINI_EMBEDDING_MODEL`: Tên model dùng để nhúng text thành vector (VD: `gemini-embedding-2`).
- `GEMINI_EMBEDDING_DIM`: Kích thước vector đầu ra (VD: `768`).
- `GEMINI_GENERATION_MODEL`: Tên model dùng để sinh câu trả lời tổng hợp (VD: `gemini-2.5-flash`).
- `DEFAULT_TOP_K`: Số lượng evidence tối đa lấy ra từ ChromaDB mỗi lần query (VD: `5`).
- `RAG_MAX_DISTANCE`: Ngưỡng chặn Cosine distance để loại bỏ chunk không liên quan.

## 10. Lệnh validate
Kiểm tra tính hợp lệ của dữ liệu đầu vào.
```bash
<python-path> rag_foundation/buoi_07/rag.py validate --strategy hierarchical
```

## 11. Lệnh status
Xem trạng thái Collection hiện tại có tồn tại hay không.
```bash
<python-path> rag_foundation/buoi_07/rag.py status --strategy hierarchical
```

## 12. Lệnh index
Thực hiện tạo Vector Embeddings và đẩy vào DB.
```bash
<python-path> rag_foundation/buoi_07/rag.py index --strategy hierarchical
```

## 13. Lệnh reset đúng collection
Nếu bị lệch Metadata hoặc bạn muốn xóa dữ liệu cũ trong collection hiện tại.
```bash
<python-path> rag_foundation/buoi_07/rag.py index --strategy hierarchical --reset
```

## 14. Lệnh query CLI
Kiểm tra luồng hỏi đáp trên giao diện dòng lệnh.
```bash
<python-path> rag_foundation/buoi_07/rag.py query --strategy hierarchical --top-k 5 --question "Thế nào là RAG?"
```

## 15. Lệnh chạy test
Chạy toàn bộ Unit Tests cục bộ (không dùng Internet).
```bash
<python-path> -m unittest discover -s rag_foundation/buoi_07/tests -v
```

## 16. Lệnh chạy Streamlit
Khởi chạy giao diện người dùng.
```bash
<python-path> -m streamlit run rag_foundation/buoi_07/app.py
```

## 17. Giải thích thuật ngữ
- **strategy**: Chiến lược chia nhỏ văn bản (VD: theo độ dài, theo ngữ nghĩa, theo cấp bậc tiêu đề).
- **embedding model**: AI chuyển đổi ngôn ngữ con người thành tọa độ số.
- **embedding dimension**: Số lượng tọa độ chiều không gian (ví dụ 768).
- **collection identity**: ChromaDB phân tách từng kho vector độc lập với mã hash riêng.
- **top-k**: Khống chế số lượng mẩu tin lớn nhất gửi cho AI đọc.
- **cosine distance**: Thuật toán đo khoảng cách hai góc vector. (Khoảng cách thấp = độ liên quan cao).
- **RAG_MAX_DISTANCE**: Hằng số chặn ngưỡng. Các vector quá xa ngưỡng này sẽ bị loại đi.
- **confidence gate**: "Cổng kiểm soát", không cho phép AI tự chém gió nếu không có bất cứ chunk nào vượt qua ngưỡng RAG_MAX_DISTANCE.
- **retrieval-only**: Tình trạng đã có tài liệu trả về, nhưng AI bị lỗi hoặc từ chối sinh chữ tổng hợp.
- **citation**: Nhãn trích dẫn trong văn bản `[E1]` được tự động ánh xạ ngược thành link Nguồn minh bạch.

## 18. Cách dừng Streamlit bằng Ctrl+C
Nếu bạn muốn tắt ứng dụng hoặc giải phóng cổng mạng, hãy vào cửa sổ Terminal đang chạy và nhấn tổ hợp phím `Ctrl + C`.

## 19. Troubleshooting
- **thiếu package**: Hãy chạy lệnh `pip install -r requirements.txt`.
- **sai interpreter**: Kiểm tra kĩ bạn đang gọi đúng đường dẫn của `.venv/bin/python` hay chưa.
- **thiếu API key**: Ứng dụng báo lỗi thiếu Key, hãy mở `.env` và điền chuỗi ký tự Google API vào.
- **collection rỗng**: Bạn phải thực thi Lệnh index trước khi chạy Query.
- **model/dimension mismatch**: Đã xảy ra xung đột khi bạn đổi cấu hình. Vui lòng thêm `--reset` khi index lại.
- **JSON lỗi**: Dữ liệu JSON ở Buổi 05 có thể bị hỏng syntax, hãy sinh lại.
- **embedding lỗi/rate limit**: Google API có thể chặn số lượng yêu cầu quá nhanh. Lệnh index được làm idempotent để tiếp tục khi lỗi, nhưng bạn cần cẩn thận.

## 20. Giới hạn của demo
- Hệ thống xử lý tuyến tính từng chunk, chưa tối ưu đa luồng.
- Bộ lọc Retrieval hoàn toàn dựa trên Semantic Search, chưa lai ghép với Keyword (BM25).

## 21. Cảnh báo
- ⚠️ Hệ thống hỏi đáp này **không phải tư vấn pháp lý**, mọi câu trả lời chỉ mang tính chất tham khảo minh họa từ văn bản nội bộ.
- ⚠️ Hằng số Threshold (RAG_MAX_DISTANCE) cần được hiệu chỉnh thêm trên dữ liệu thực tế.
- ⚠️ Vector Search có thể bỏ sót các thông tin rải rác ở xa hoặc ẩn ý (Miss Retrieval).
- ⚠️ Dữ liệu nội bộ khi thực hiện Lập chỉ mục hoặc Hỏi đáp sẽ được đóng gói truyền lên hệ thống Google. Tuyệt đối chỉ dùng các bộ dữ liệu mà bạn đã được cấp quyền truyền tải ra bên ngoài.

---

## Phần 3 - Thực nghiệm truy vấn thủ công (Manual Test)

Dưới đây là 3 câu hỏi minh họa nhằm kiểm thử khả năng tìm kiếm của RAG. Hãy chạy trên tab Query sau khi bạn đã index dữ liệu:

### A. Có khả năng thuộc tài liệu
> `Cơ cấu lại thời hạn trả nợ được quy định như thế nào?`

### B. Có khả năng thuộc tài liệu
> `Việc phân loại nợ và trích lập dự phòng được thực hiện như thế nào?`

### C. Ngoài phạm vi
> `Ngân hàng nào có lãi suất tiết kiệm cao nhất hôm nay?`
> 
> *Kỳ vọng mong muốn*: Cổng kiểm soát (Confidence Gate) sẽ đánh rớt tất cả evidence. Hệ thống phải trả lời `Không tìm thấy đủ thông tin liên quan trong tài liệu đã cung cấp.` mà không tự bịa đặt bất kỳ ngân hàng/lãi suất nào.
