import os
import streamlit as st
from multi_hop import MultiHopRAG
from llm_integration import generate_answer

# Cấu hình trang
st.set_page_config(
    page_title="Graph RAG Law QA System",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cấu hình kết nối mặc định
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "abcd1234")
MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"


# Khởi tạo RAG Engine với cache resource
@st.cache_resource
def get_rag_engine():
    try:
        rag = MultiHopRAG(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, MODEL_NAME)
        rag.create_vector_index()
        return rag
    except Exception as e:
        return None

# Sidebar - Cấu hình hệ thống
with st.sidebar:
    st.title(":material/settings: Cấu hình hệ thống")
    
    # 1. Trạng thái kết nối Neo4j
    rag = get_rag_engine()
    if rag:
        st.success(":material/check_circle: Neo4j: Đã kết nối (`kb-hops`)", icon="✅")
    else:
        st.error(":material/error: Neo4j: Chưa kết nối", icon="🚨")
        
    # Cấu hình API Key từ sidebar hoặc môi trường
    api_key_input = st.text_input(
        "Gemini API Key",
        value=os.environ.get("GEMINI_API_KEY", ""),
        type="password",
        help="Nhập GEMINI_API_KEY của bạn"
    )
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input  
    # 3. Điều chỉnh tham số Graph RAG
    st.subheader(":material/tune: Tham số tra cứu")
    
    # Dùng segmented_control hiện đại thay cho slider đơn điệu
    hop_option = st.segmented_control(
        "Số bước nhảy đồ thị (Multi-hop Hops):",
        options=["0 Hops (Chỉ Vector)", "1 Hop (Mở rộng Đồ thị)", "2 Hops (Duyệt Đồ thị Sâu)"],
        default="1 Hop (Mở rộng Đồ thị)"
    )
    
    # Chuyển đổi lựa chọn thành số integer
    if "0 Hops" in hop_option:
        hops = 0
    elif "1 Hop" in hop_option:
        hops = 1
    else:
        hops = 2
        
    top_k = st.slider("Số phân đoạn gốc (Top-K Vector Match):", min_value=1, max_value=5, value=2, step=1)
    
    st.divider()
    with st.container(border=True):
        st.markdown("**💡 Hướng dẫn Đa bước (Multi-hop):**")
        st.caption("- **0 Hops**: Chỉ truy vấn đoạn văn bản khớp vector trực tiếp.")
        st.caption("- **1-2 Hops**: Tự động mở rộng sang các văn bản liên quan qua mối quan hệ `CAN_CU`, `THAY_THE`, `HOP_NHAT`, `SUA_DOI_BO_SUNG`.")

# Tiêu đề chính
st.title("⚖️ Hệ thống Hỏi Đáp Luật Việt Nam (Multi-hop Graph RAG)")
st.caption("Ứng dụng kết hợp Tìm kiếm Vector nhúng, Duyệt đồ thị tri thức Neo4j và Tổng hợp câu trả lời từ Gemini LLM")

# Tạo Tabs chức năng chính
tab1, tab2, tab3 = st.tabs([
    ":material/gavel: Tra cứu & Hỏi đáp",
    ":material/analytics: Báo cáo đánh giá (qa_comparison.md)",
    ":material/schema: Cấu trúc Đồ thị Tri thức"
])

# ================= TAB 1: TRA CỨU HỎI ĐÁP =================
with tab1:
    col_input, col_preset = st.columns([3, 2])
    
    sample_questions = [
        "-- Chọn câu hỏi kiểm thử mẫu --",
        "Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?",
        "Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào, và quy định về hồ sơ, thủ tục cấp giấy phép lần đầu của ngân hàng thương mại gồm những tài liệu gì?",
        "Thông tư số 01/2025/TT-NHNN quy định về cấp giấy phép quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi văn bản nào, và những nội dung sửa đổi bổ sung chính là gì?",
        "Thông tư số 41/2016/TT-NHNN về tỷ lệ an toàn vốn của ngân hàng căn cứ vào luật nào, và luật đó quy định chức năng nhiệm vụ của cơ quan nào?",
        "Hoạt động giao nhận, vận chuyển tiền mặt và tài sản quý của Ngân hàng Nhà nước được điều chỉnh bởi Thông tư nào, và Thông tư đó có được sửa đổi bổ sung bởi văn bản nào không?"
    ]
    
    with col_preset:
        selected_sample = st.selectbox("📋 Chọn nhanh câu hỏi kiểm thử:", sample_questions)
        
    with col_input:
        default_query = selected_sample if selected_sample != "-- Chọn câu hỏi mẫu --" else ""
        user_query = st.text_area("❓ Nhập câu hỏi pháp lý của bạn:", value=default_query, height=100, placeholder="Ví dụ: Nghị định 46/2023/NĐ-CP quy định về những vấn đề gì?")

    btn_search = st.button("🚀 Tra cứu Ngữ cảnh & Tạo Câu trả lời", type="primary", width="stretch")

    if btn_search:
        if not user_query.strip():
            st.warning("Vui lòng nhập nội dung câu hỏi trước khi tìm kiếm!")
        else:
            if not rag:
                st.error("Chưa thể kết nối tới cơ sở dữ liệu Neo4j. Vui lòng kiểm tra lại dịch vụ Neo4j cục bộ.")
            else:
                with st.spinner("🔍 Đang nhúng câu hỏi, truy vấn Vector và duyệt đồ thị Neo4j..."):
                    context_list = rag.search_context(user_query, top_k=top_k, hops=hops)
                
                st.toast(f"Đã thu thập {len(context_list)} đoạn ngữ cảnh với cấu hình {hops} hops!", icon="✅")
                
                # Hiển thị kết quả chia làm 2 cột
                col_res, col_graph = st.columns([3, 2])
                
                with col_res:
                    st.subheader(":material/smart_toy: Câu trả lời từ AI (Gemini)")
                    with st.container(border=True):
                        with st.spinner("🤖 Gemini AI đang phân tích ngữ cảnh và tổng hợp câu trả lời..."):
                            answer = generate_answer(user_query, context_list)
                            st.markdown(answer)
                            
                with col_graph:
                    st.subheader(f":material/account_tree: Ngữ cảnh từ Graph ({len(context_list)} đoạn)")
                    if not context_list:
                        st.info("Không tìm thấy đoạn ngữ cảnh nào phù hợp trong CSDL.")
                    else:
                        for idx, ctx in enumerate(context_list):
                            ctx_type = ctx.get('type', '')
                            is_direct = "Trực tiếp" in ctx_type
                            title_prefix = "🟢 [Direct Match]" if is_direct else "🔵 [Multi-hop Match]"
                            
                            with st.expander(f"{title_prefix} {ctx.get('title')[:35]}..."):
                                st.markdown(f"**Loại kết quả:** `{ctx_type}`")
                                st.markdown(f"**Văn bản:** {ctx.get('title')}")
                                st.markdown(f"**Mã văn bản (ID):** `{ctx.get('doc_id')}`")
                                st.divider()
                                st.markdown(f"**Nội dung phân đoạn:**\n> {ctx.get('text')}")

# ================= TAB 2: BÁO CÁO ĐÁNH GIÁ (STEP 4) =================
with tab2:
    st.subheader("📊 Báo cáo kết quả kiểm thử 5 tình huống pháp lý phức tạp (qa_comparison.md)")
    st.caption("Báo cáo so sánh câu trả lời của LLM khi thay đổi các bước nhảy (0 hops vs 1 hop vs 2 hops)")
    
    report_file = "qa_comparison.md"
    if os.path.exists(report_file):
        with open(report_file, "r", encoding="utf-8") as f:
            report_content = f.read()
        
        with st.container(border=True):
            st.markdown(report_content)
    else:
        st.warning("Chưa tìm thấy tệp báo cáo `qa_comparison.md`. Bạn có thể chạy lệnh `python run_evaluation.py` để tạo báo cáo này.")

# ================= TAB 3: CẤU TRÚC ĐỒ THỊ TRI THỨC =================
with tab3:
    st.subheader("🕸️ Lược đồ dữ liệu đồ thị tri thức (Graph Schema)")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric(label="Số nút Document", value="15")
    with col_m2:
        st.metric(label="Số mối quan hệ giữa các Luật", value="8")
    with col_m3:
        st.metric(label="Vector Index Dimensions", value="384")
    with col_m4:
        st.metric(label="Mô hình Embedding", value="vi-distilled-msmarco")
        
    st.divider()
    
    with st.container(border=True):
        st.markdown("""
        ### Cấu trúc Các nút & Quan hệ trong Neo4j (`kb-hops`)
        
        - **Nút (Nodes):**
          - `(:Document)`: Siêu dữ liệu của các văn bản pháp luật (Tiêu đề, Số ký hiệu, Ngày ban hành...).
          - `(:Chunk)`: Các đoạn văn bản đã chia nhỏ kèm Vector nhúng (Dense Embedding).
        - **Mối quan hệ (Relationships):**
          - `(:Chunk)-[:PART_OF]->(:Document)`: Đoạn văn bản thuộc về tài liệu nào.
          - `(:Chunk)-[:NEXT]->(:Chunk)`: Liên kết trình tự đọc liền kề giữa các phân đoạn.
          - `(:Document)-[:CAN_CU]->(:Document)`: Căn cứ pháp lý.
          - `(:Document)-[:THAY_THE]->(:Document)`: Thay thế văn bản luật cũ.
          - `(:Document)-[:HOP_NHAT]->(:Document)`: Hợp nhất các văn bản.
          - `(:Document)-[:SUA_DOI_BO_SUNG]->(:Document)`: Sửa đổi và bổ sung luật.
        """)
