import streamlit as st
import os
import json
import pandas as pd
from pathlib import Path

from advanced_rag import (
    load_config, load_chunks, get_status, 
    query_pipeline, DEFAULT_INPUT_DIR
)

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(page_title="Advanced RAG", layout="wide")

@st.cache_data
def get_bm25_corpus(strategy):
    try:
        chunks, _ = load_chunks(DEFAULT_INPUT_DIR, strategy)
        return chunks
    except Exception:
        return []

if 'last_query' not in st.session_state:
    st.session_state['last_query'] = ""
if 'last_result' not in st.session_state:
    st.session_state['last_result'] = None

st.sidebar.markdown("### ⚡ Advanced RAG Controls")
try:
    config = load_config()
    
    strategy = st.sidebar.selectbox("Chiến lược Chunking (Strategy)", ["hierarchical", "semantic", "fixed-size"])
    mode = st.sidebar.selectbox("Chế độ Retrieval Mặc định", ["hybrid_rerank", "hybrid", "semantic", "bm25"])

    with st.sidebar.expander("⚙️ Tham số RAG & Thresholds"):
        st.write(f"**BM25/Semantic K**: {config['BM25_CANDIDATES']}/{config['SEMANTIC_CANDIDATES']}")
        st.write(f"**RRF k**: {config['RRF_K']} | **Weights**: {config['RRF_BM25_WEIGHT']}/{config['RRF_SEMANTIC_WEIGHT']}")
        st.write(f"**Rerank K**: {config['RERANK_CANDIDATES']} | **Min Score**: {config['RERANK_MIN_SCORE']}")
        st.write(f"**Final Top-K**: {config['FINAL_TOP_K']}")

    st.sidebar.markdown("### 🔍 Trạng thái Hệ thống (Read-Only)")
    
    # Cột trạng thái 
    col_status1, col_status2 = st.sidebar.columns(2)
    with col_status1:
        st.success(f"API Key: {'Có' if config['GEMINI_API_KEY'] else 'Thiếu'}")
    with col_status2:
        st.warning(f"Reranker:\nChưa cache")

    try:
        status = get_status(strategy)
        col_name = status.get('semantic_collection_name', 'N/A')
        count = status.get('collection_count', 0)
        
        st.sidebar.info(f"**Corpus Chunks**: {count}\n\n**Collection**: `{col_name}`\n\n**Collection Records**: {count}\n\n**Embedding Model**: `gemini-embedding-2 (768d)`\n\n**Reranker Model**: `{config['RERANKER_MODEL']}`")
        if count == 0:
            st.sidebar.warning("Collection rỗng hoặc chưa index. Hãy chạy lệnh `prepare-semantic`.")
    except Exception as e:
        st.sidebar.error(f"Lỗi Chroma: {e}")

except Exception as e:
    st.sidebar.error(f"Lỗi Config: {e}")
    st.stop()


st.markdown("<h1><span style='color: #4285F4;'>🛡️</span> Advanced RAG Architecture Dashboard</h1>", unsafe_allow_html=True)
st.caption("Buổi 08: Lexical BM25 -> Semantic Dense Candidate -> RRF Fusion -> Cross-Encoder Reranker -> Grounded Answer")

tab1, tab2, tab3, tab4 = st.tabs(["Hỏi đáp Advanced RAG", "So sánh Retrieval", "Pipeline Trace", "Đánh giá Evaluation"])

with tab1:
    st.markdown("### Hỏi đáp Trực tiếp với Pipeline Advanced RAG")
    question = st.text_input("Nhập câu hỏi truy vấn pháp lý / tài liệu ngân hàng:", value=st.session_state['last_query'])
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        exec_mode = st.selectbox("Chế độ Retrieval thực thi", ["hybrid_rerank", "hybrid", "semantic", "bm25"], index=["hybrid_rerank", "hybrid", "semantic", "bm25"].index(mode))
    with col2:
        top_k = st.number_input("Top-K Chứng cứ", min_value=1, max_value=20, value=config['FINAL_TOP_K'])
    with col3:
        st.write("")
        st.write("")
        submit_btn = st.button("🚀 Chạy RAG Pipeline", type="primary", use_container_width=True)

    if submit_btn:
        if not question.strip():
            st.warning("Vui lòng nhập câu hỏi.")
        else:
            with st.spinner(f"Đang xử lý bằng mode {exec_mode}..."):
                try:
                    res = query_pipeline(question, strategy, exec_mode)
                    st.session_state['last_query'] = question
                    st.session_state['last_result'] = res
                except Exception as e:
                    st.error(f"Lỗi hệ thống không xác định: {e}")

    if st.session_state['last_result']:
        res = st.session_state['last_result']
        st.subheader("Kết quả")
        if res['status'] == 'reranker_unavailable':
            st.error("Reranker Model chưa sẵn sàng hoặc gặp lỗi tải. Ở lần chạy đầu tiên, hệ thống cần Internet và thời gian tải model. Vui lòng chạy lệnh CLI để tải hoặc thử lại.")
            for w in res.get('warnings', []):
                st.error(w)
        elif res['status'] == 'insufficient_evidence':
            st.warning(res['answer'])
        elif res['status'] == 'retrieval_error':
            st.error("Lỗi truy xuất dữ liệu.")
            for w in res.get('warnings', []):
                st.error(w)
        else:
            st.success("Tạo câu trả lời thành công!")
            st.markdown(res['answer'])
            
            if res.get('citations'):
                st.markdown("### Trích dẫn:")
                for cite in res['citations']:
                    st.markdown(f"- **[{cite['evidence_id']}]** {cite['display']}")
            
            if res.get('warnings'):
                for w in res['warnings']:
                    st.warning(w)

            st.markdown("### Bằng chứng (Evidence)")
            for i, ev in enumerate(res['evidence']):
                acc_icon = "✅" if ev.get('accepted') else "❌"
                with st.expander(f"[{i+1}] {acc_icon} Chunk: {ev['chunk_id']}"):
                    st.markdown(f"**Source:** {ev['source']} (Trang {ev['page_start']}-{ev['page_end']})")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("BM25 Rank", ev.get('bm25_rank') or "-")
                    col2.metric("Semantic Rank", ev.get('semantic_rank') or "-")
                    col3.metric("Fused Rank", ev.get('fused_rank') or "-")
                    col4.metric("Rerank Score", f"{ev.get('rerank_score'):.4f}" if ev.get('rerank_score') is not None else "-")
                    col5.metric("Rank Change", f"{ev.get('rank_change'):+d}" if ev.get('rank_change') is not None else "-")
                    st.write(ev['text'])

with tab2:
    st.subheader("So sánh 4 Modes (Chỉ Retrieval)")
    if st.button("So sánh"):
        if not question:
            st.warning("Vui lòng nhập câu hỏi ở Tab 1")
        else:
            with st.spinner("Đang chạy truy xuất qua 4 modes..."):
                modes = ['bm25', 'semantic', 'hybrid', 'hybrid_rerank']
                results = {}
                for m in modes:
                    results[m] = query_pipeline(question, strategy, m, fake_gen=lambda x: "", fake_rerank=None)
                
                all_chunks = {}
                for m in modes:
                    if 'evidence' in results[m]:
                        for i, ev in enumerate(results[m]['evidence']):
                            cid = ev['chunk_id']
                            if cid not in all_chunks:
                                all_chunks[cid] = {'bm25_rank': '-', 'semantic_rank': '-', 'hybrid_fused_rank': '-', 'hybrid_rerank_rank': '-', 'rank_change': '-'}
                            
                            all_chunks[cid][f"{m}_rank" if m != 'hybrid' else 'hybrid_fused_rank'] = str(i+1)
                            if m == 'hybrid_rerank' and ev.get('rank_change') is not None:
                                all_chunks[cid]['rank_change'] = f"{ev['rank_change']:+d}"
                
                if all_chunks:
                    df = pd.DataFrame.from_dict(all_chunks, orient='index')
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("Không có chunk nào được truy xuất.")

with tab3:
    st.subheader("Pipeline Trace")
    if st.session_state['last_result'] and 'trace' in st.session_state['last_result']:
        trace = st.session_state['last_result']['trace']
        
        st.markdown("### Dòng chảy Candidate")
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("BM25 Cands", trace.get('bm25_candidates', 0))
        col2.metric("Semantic Cands", trace.get('semantic_candidates', 0))
        col3.metric("Union / Overlap", f"{trace.get('union', 0)} / {trace.get('overlap', 0)}")
        col4.metric("Reranked", trace.get('reranked', 0))
        col5.metric("Accepted", trace.get('accepted', 0))
        
        st.markdown("### Độ trễ (Latency)")
        lat = trace.get('latency_ms', {})
        if lat:
            l_df = pd.DataFrame(list(lat.items()), columns=["Stage", "Latency (ms)"])
            l_df['Latency (ms)'] = l_df['Latency (ms)'].apply(lambda x: f"{x:.2f}")
            st.table(l_df)
        
        st.info("Chú giải: BM25 score cao hơn là tốt hơn | Cosine distance thấp hơn là tốt hơn | RRF và Rerank score cao hơn là tốt hơn (Lưu ý: Rerank score không phải là xác suất).")
    else:
        st.info("Hãy chạy một truy vấn ở Tab 1 để xem Trace.")

with tab4:
    st.subheader("Báo cáo Đánh giá (Evaluation)")
    report_path = BASE_DIR / "reports" / "eval_report.json"
    if report_path.exists():
        with open(report_path, 'r', encoding='utf-8') as f:
            try:
                report = json.load(f)
                st.json(report)
                
                # Render logic metrics if available
                # e.g., Recall@K, MRR, nDCG
            except:
                st.warning("File báo cáo không đúng định dạng JSON hợp lệ.")
    else:
        st.info("Chưa có báo cáo đánh giá. Vui lòng chạy evaluate.py (Bước 10) để tạo report hàng loạt.")
        st.warning("EVAL: Không kết luận mode tốt nhất (winner) khi chưa có report hợp lệ.")
