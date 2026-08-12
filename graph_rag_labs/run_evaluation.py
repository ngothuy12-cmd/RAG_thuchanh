import os
import time
from multi_hop import MultiHopRAG
from llm_integration import generate_answer

# Cấu hình kết nối
NEO4J_URI = "bolt://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "abcd1234"
MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"

# 5 câu hỏi kiểm thử theo yêu cầu
TEST_QUESTIONS = [
    {
        "id": 1,
        "question": "Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?"
    },
    {
        "id": 2,
        "question": "Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào, và quy định về hồ sơ, thủ tục cấp giấy phép lần đầu của ngân hàng thương mại gồm những tài liệu gì?"
    },
    {
        "id": 3,
        "question": "Thông tư số 01/2025/TT-NHNN quy định về cấp giấy phép quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi văn bản nào, và những nội dung sửa đổi bổ sung chính là gì?"
    },
    {
        "id": 4,
        "question": "Thông tư số 41/2016/TT-NHNN về tỷ lệ an toàn vốn của ngân hàng căn cứ vào luật nào, và luật đó quy định chức năng nhiệm vụ của cơ quan nào?"
    },
    {
        "id": 5,
        "question": "Hoạt động giao nhận, vận chuyển tiền mặt và tài sản quý của Ngân hàng Nhà nước được điều chỉnh bởi Thông tư nào, và Thông tư đó có được sửa đổi bổ sung bởi văn bản nào không?"
    }
]

def run_pipeline_evaluation():
    print("Khởi tạo RAG Evaluator...")
    rag = MultiHopRAG(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, MODEL_NAME)
    rag.create_vector_index()

    markdown_report = "# Báo cáo Đánh giá So sánh Hệ thống Hỏi Đáp Graph RAG Đa Bước (Multi-hop)\n\n"
    markdown_report += "Báo cáo này ghi nhận kết quả so sánh câu trả lời của mô hình LLM khi thay đổi số bước nhảy (hops = 0, hops = 1, hops = 2) trong đồ thị tri thức Neo4j.\n\n"
    markdown_report += "---\n\n"

    for item in TEST_QUESTIONS:
        q_id = item["id"]
        question = item["question"]
        print(f"\n==================================================")
        print(f"Đang xử lý Câu hỏi {q_id}: {question}")
        print(f"==================================================")

        markdown_report += f"## Câu hỏi {q_id}: {question}\n\n"

        for hops in [0, 1, 2]:
            print(f" -> Chạy thử nghiệm với hops = {hops}...")
            # Lấy top 3 vector matches
            context = rag.search_context(question, top_k=3, hops=hops)
            
            # Gọi LLM
            answer = generate_answer(question, context)
            
            # Thêm thông tin vào báo cáo markdown
            markdown_report += f"### 🔹 Số bước nhảy: `{hops} hops`\n"
            markdown_report += f"**Số lượng ngữ cảnh thu thập được:** {len(context)} đoạn văn bản.\n\n"
            markdown_report += f"**Các tài liệu ngữ cảnh:**\n"
            for ctx in context:
                markdown_report += f"- [{ctx.get('type')}] **{ctx.get('title')}** (ID: {ctx.get('doc_id')})\n"
            
            markdown_report += f"\n**Câu trả lời của AI:**\n"
            markdown_report += f"> {answer.strip().replace('\n', '\n> ')}\n\n"
            
            # Tránh overload API rate limit
            time.sleep(2)

        markdown_report += "\n---\n\n"

    rag.close()

    # Ghi báo cáo ra file qa_comparison.md
    output_filename = "qa_comparison.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(markdown_report)

    print(f"\n✅ ĐÃ HOÀN THÀNH ĐÁNH GIÁ! Báo cáo chi tiết đã được ghi vào tệp `{output_filename}`.")

if __name__ == "__main__":
    run_pipeline_evaluation()
