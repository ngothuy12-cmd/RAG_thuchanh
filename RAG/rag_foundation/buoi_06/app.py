import streamlit as st
import rag
import importlib
importlib.reload(rag)

import os
from dotenv import load_dotenv

st.set_page_config(page_title="RAG Chatbot", page_icon="🤖")

load_dotenv(override=True)

# --- Đọc trạng thái hệ thống ---
try:
    status_data = rag.status()
    pg_status = "🟢 Hoạt động" if status_data["db_type"] == "postgres" else "🔴 Không (Dùng SQLite)"
except Exception:
    pg_status = "🔴 Lỗi kết nối"

chroma_status = "🟢 Hoạt động" if rag.get_chroma_collection() else "🔴 Không hoạt động"
gemini_status = "🟢 Có" if os.getenv("GEMINI_API_KEY") else "🔴 Thiếu"

# --- Sidebar ---
with st.sidebar:
    st.header("Trạng thái")
    st.write(f"**PostgreSQL**: {pg_status}")
    st.write(f"**ChromaDB**: {chroma_status}")
    st.write(f"**Gemini API Key**: {gemini_status}")

# --- Main Area ---
st.title("Hệ thống RAG - Buổi 6")

if st.button("Build Index"):
    with st.spinner("Đang xử lý dữ liệu..."):
        res = rag.index()
    st.success(res)

st.divider()

question = st.text_input("Nhập câu hỏi của bạn:")
if st.button("Hỏi"):
    if question:
        with st.spinner("Pipeline: Question ➔ Top-k ➔ Gemini ➔ Answer"):
            contexts, answer = rag.ask(question, k=3)
            
            # --- Kết quả Top-k ---
            st.subheader("Kết quả Top-k (Retrieval)")
            if contexts:
                for i, ctx in enumerate(contexts):
                    with st.expander(f"Chunk {i+1}"):
                        st.write(ctx)
            else:
                st.write("Không tìm thấy kết quả Retrieval.")
            
            # --- Answer ---
            st.subheader("Answer (Câu trả lời)")
            if answer:
                st.write(answer)
            elif contexts:
                st.info("Chế độ Retrieval Only (Không gọi Gemini do thiếu API Key).")
            else:
                st.error(answer) # Trường hợp string chứa lỗi trả về từ ask() nếu mảng contexts rỗng
    else:
        st.warning("Vui lòng nhập câu hỏi.")
