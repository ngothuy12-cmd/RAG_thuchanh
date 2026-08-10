"""
Streamlit App for Buổi 07.
"""
import streamlit as st
from pathlib import Path
import rag

st.set_page_config(page_title="RAG Pipeline Buổi 07", layout="wide")

if 'strategy' not in st.session_state:
    st.session_state.strategy = 'hierarchical'
if 'top_k' not in st.session_state:
    st.session_state.top_k = 5

def update_strategy():
    pass

st.title("Hệ thống RAG - Buổi 07")

st.sidebar.header("Cấu hình & Trạng thái")

strategy = st.sidebar.selectbox(
    "Strategy", 
    ['hierarchical', 'semantic', 'fixed-size'], 
    key='strategy',
    on_change=update_strategy
)
top_k = st.sidebar.number_input("Top K", min_value=1, max_value=10, key='top_k')

try:
    status = rag.get_status(st.session_state.strategy)
    st.sidebar.markdown(f"**API Key:** {'Có' if status['has_key'] else 'Thiếu'}")
    st.sidebar.markdown(f"**Embedding Model:** {status['embedding_model']}")
    st.sidebar.markdown(f"**Dimension:** {status['embedding_dim']}")
    st.sidebar.markdown(f"**Generation Model:** {status.get('generation_model', 'N/A')}")
    st.sidebar.markdown(f"**Max Distance:** {status.get('max_distance', 'N/A')}")
    st.sidebar.markdown(f"**Collection:** `{status['collection_name']}`")
    st.sidebar.markdown(f"**Trạng thái:** {'Đã tạo' if status['exists'] else 'Chưa tạo'}")
    st.sidebar.markdown(f"**Số Chunk:** {status['count']}")
except Exception as e:
    st.sidebar.error(f"Lỗi đọc trạng thái: {str(e)}")
    status = None

tab_index, tab_query = st.tabs(["Quản lý Dữ liệu (Index)", "Hỏi Đáp (Query)"])

with tab_index:
    st.header("Lập chỉ mục dữ liệu")
    reset_index = st.checkbox("Reset collection trước khi index", value=False)
    
    if st.button("Index dữ liệu", type="primary"):
        if not status or not status['has_key']:
            st.error("Thiếu API key. Hãy cấu hình GEMINI_API_KEY trong file .env")
        else:
            with st.spinner("Đang xử lý index..."):
                try:
                    res = rag.do_index(st.session_state.strategy, reset=reset_index)
                    st.success(f"Đã index thành công vào collection `{res['collection_name']}`")
                    st.info(f"Số chunk hiện tại: {res['count_after']}")
                    if 'stats' in res:
                        st.text(f"Text rỗng bị bỏ qua: {res['stats'].get('empty_text_skipped', 0)}")
                except Exception as e:
                    st.error(f"Lỗi khi index: {str(e)}")

with tab_query:
    st.header("Truy vấn tài liệu")
    question = st.text_area("Nhập câu hỏi:", height=100)
    
    can_query = True
    if not status or not status['has_key']:
        st.warning("Thiếu API key. Cần cung cấp trong .env để query.")
        can_query = False
    elif not status['exists']:
        st.warning("Collection chưa tồn tại. Vui lòng index trước.")
        can_query = False
    elif status['count'] == 0:
        st.warning("Collection rỗng. Vui lòng index trước.")
        can_query = False
        
    if st.button("Gửi câu hỏi", type="primary", disabled=not can_query):
        if not question.strip():
            st.warning("Vui lòng nhập câu hỏi.")
        else:
            with st.spinner("Đang tìm kiếm và tổng hợp câu trả lời..."):
                try:
                    res = rag.ask_question(question.strip(), st.session_state.top_k, st.session_state.strategy)
                    
                    st.subheader("Trả lời")
                    
                    if res['status'] == 'insufficient_evidence':
                        st.info(res['answer'])
                    elif res['status'] == 'retrieval_only':
                        st.warning(res['answer'])
                    else:
                        st.markdown(res['answer'])
                        
                    if res.get('warnings'):
                        for w in res['warnings']:
                            st.warning(w)
                            
                    if res.get('citations'):
                        st.markdown("**Citations:**")
                        for cit in res['citations']:
                            st.markdown(f"- {cit['display']}")
                            
                    st.subheader("Nguồn tham khảo")
                    if not res.get('evidence'):
                        st.info("Chưa có evidence.")
                    else:
                        for ev in res['evidence']:
                            page_str = f"tr. {ev['page_start']}" if ev['page_start'] == ev['page_end'] else f"tr. {ev['page_start']}-{ev['page_end']}"
                            acc_str = "✅ Đạt" if ev['accepted'] else "❌ Không đạt"
                            
                            with st.expander(f"{ev['source']} – {page_str} – {ev['chunk_id']} ({acc_str})"):
                                st.markdown(f"**Evidence ID:** {ev['evidence_id']}")
                                st.markdown(f"**Distance:** {ev['distance']:.4f} *(Distance thấp hơn thường liên quan hơn)*")
                                st.markdown(f"**Trạng thái:** {'Được dùng để tạo câu trả lời' if ev['accepted'] else 'Bị loại do không đạt ngưỡng liên quan'}")
                                st.text_area("Nội dung chunk", ev['text'], height=150, disabled=True, key=ev['chunk_id'])
                                
                except Exception as e:
                    st.error(f"Lỗi khi query: {str(e)}")
