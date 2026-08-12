import os
from google import genai
from google.genai import types
from multi_hop import MultiHopRAG

# Sử dụng GEMINI_API_KEY từ biến môi trường
API_KEY = os.environ.get("GEMINI_API_KEY", "")

def get_genai_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            return genai.Client(api_key=api_key)
        except Exception:
            return None
    return None

SYSTEM_INSTRUCTION = """
Bạn là một chuyên gia tư vấn pháp lý Việt Nam tận tâm và chính xác. Nhiệm vụ của bạn là trả lời các câu hỏi dựa trên các tài liệu luật pháp được cung cấp.

THÔNG TIN VỀ CẤU TRÚC DỮ LIỆU:
- Dữ liệu được trích xuất từ một Đồ thị tri thức (Knowledge Graph) chứa các đoạn văn bản (Chunk) và các Văn bản luật (Document).
- Các văn bản luật có các mối quan hệ với nhau như: Căn cứ (CAN_CU), Thay thế (THAY_THE), Hợp nhất (HOP_NHAT), Sửa đổi bổ sung (SUA_DOI_BO_SUNG), Văn bản bổ sung (VAN_BAN_BO_SUNG).
- Ngữ cảnh được cung cấp bao gồm các đoạn văn bản khớp trực tiếp với câu hỏi (Vector Match) và các đoạn văn bản từ các tài liệu liên quan thông qua các mối quan hệ đa bước (Multi-hop).

QUY TẮC TRẢ LỜI NGHIÊM NGẶT:
1. BẮT BUỘC CHỈ SỬ DỤNG thông tin từ phần "Ngữ cảnh (Context)" được cung cấp để trả lời.
2. Nếu ngữ cảnh KHÔNG chứa thông tin để trả lời, phải nói rõ: "Dựa trên các ngữ cảnh được cung cấp, tôi không tìm thấy thông tin để trả lời câu hỏi này." TUYỆT ĐỐI KHÔNG TỰ SUY ĐOÁN hay dùng kiến thức bên ngoài đồ thị.
3. Luôn trích dẫn rõ ràng tên văn bản (ví dụ: "Theo Thông tư 01/2025/TT-NHNN..." hoặc "Theo Nghị định 46/2023/NĐ-CP...").
4. Nếu sử dụng thông tin từ văn bản liên quan (Multi-hop), hãy giải thích mạch logic pháp lý (ví dụ: "Vamber A là căn cứ của Văn bản B, trong đó quy định...").
5. Trình bày câu trả lời rõ ràng, mạch lạc, sử dụng gạch đầu dòng nếu cần thiết để dễ đọc.
"""

def generate_answer(question, context_list):
    """
    Kết hợp câu hỏi và ngữ cảnh để gọi Gemini API.
    """
    client = get_genai_client()
    if not client:
        return "[Chưa thiết lập GEMINI_API_KEY] Vui lòng nhập GEMINI_API_KEY vào ô trên thanh Sidebar bên trái để kích hoạt AI trả lời."

    if not context_list:
        return "Không có ngữ cảnh nào được tìm thấy trong cơ sở dữ liệu để trả lời câu hỏi này."
        
    # Xây dựng prompt ngữ cảnh
    context_text = "NGỮ CẢNH (CONTEXT):\n"
    for i, ctx in enumerate(context_list):
        context_text += f"\n--- Đoạn {i+1} [{ctx.get('type', 'Unknown')}] ---\n"
        context_text += f"Văn bản: {ctx.get('title', 'Unknown')}\n"
        context_text += f"Nội dung: {ctx.get('text', '')}\n"
        
    prompt = f"{context_text}\n\nCÂU HỎI CỦA NGƯỜI DÙNG: {question}\n\nCÂU TRẢ LỜI:"
    
    # Danh sách các tên model phổ biến của Gemini để thử nghiệm
    candidate_models = [
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-2.0-flash-lite',
        'gemini-2.5-flash'
    ]
    
    last_error = ""
    for model_name in candidate_models:
        try:
            print(f"[Thử nghiệm Model] Đang thử model: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2,
                    top_p=0.95,
                    top_k=64,
                    max_output_tokens=8192,
                )
            )
            print(f"[Thành công] Đã tạo câu trả lời với model: {model_name}")
            return response.text
        except Exception as e:
            last_error = str(e)
            print(f" -> Model {model_name} không khả dụng.")
            continue
            
    # Nếu danh sách candidate thất bại, thử lấy động từ API nhưng bỏ qua các model 2.5 bị lỗi
    try:
        print("[Thử nghiệm Model] Đang quét danh sách model khả dụng từ API...")
        for m in client.models.list():
            name = m.name.replace('models/', '')
            if '2.5' in name or name in candidate_models:
                continue # Bỏ qua các model đã thử hoặc 2.5 bị lỗi
                
            try:
                print(f"[Thử nghiệm Model] Đang thử model từ API list: {name}...")
                response = client.models.generate_content(
                    model=name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.2,
                    )
                )
                print(f"[Thành công] Đã tạo câu trả lời với model: {name}")
                return response.text
            except Exception:
                continue
    except Exception:
        pass
        
    return f"Lỗi: Không tìm thấy mô hình Gemini nào hoạt động với API Key của bạn.\nChi tiết lỗi cuối cùng: {last_error}"

def main():
    # Cấu hình kết nối Neo4j
    NEO4J_URI = "bolt://127.0.0.1:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "abcd1234"
    MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"

    print("Đang khởi tạo hệ thống Graph RAG...")
    rag = MultiHopRAG(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, MODEL_NAME)
    
    question = "Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào?"
    hops = 1
    
    print(f"\n[1] Đang tìm kiếm ngữ cảnh cho câu hỏi: '{question}' (hops={hops})...")
    context = rag.search_context(question, top_k=2, hops=hops)
    
    print(f"\n[2] Đã tìm thấy {len(context)} đoạn ngữ cảnh. Đang gọi Gemini API để tạo câu trả lời...")
    
    # Chỉ gọi API nếu đã có key
    if API_KEY:
        answer = generate_answer(question, context)
        print("\n" + "="*50)
        print("CÂU TRẢ LỜI TỪ HỆ THỐNG:")
        print("="*50)
        print(answer)
        print("="*50)
    else:
        print("\nBỏ qua việc gọi Gemini vì chưa cấu hình GEMINI_API_KEY.")
        print("\nNgữ cảnh tìm được:")
        for i, ctx in enumerate(context):
            print(f"- [{ctx.get('type')}] {ctx.get('title')}: {ctx.get('text')[:100]}...")
            
    rag.close()

if __name__ == "__main__":
    main()
