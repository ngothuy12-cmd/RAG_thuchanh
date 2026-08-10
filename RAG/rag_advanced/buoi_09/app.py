import os
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from hierarchical_rag import (
    load_config, load_and_validate_chunks, load_hierarchy_store, execute_pipeline
)
from advanced_rag import get_status
from ui_helpers import (
    format_citation, build_query_child_matrix, build_parent_tree_data,
    map_status_to_warning, build_compare_row
)

st.set_page_config(page_title="RAG Buổi 09", layout="wide")

st.title("RAG Foundation — Buổi 09: Multi-query & Parent–Child Retrieval")
st.markdown("`Query fan-out → Hybrid per query → Cross-query RRF → Parent expansion → Parent rerank`")

# Load baseline config
config = load_config()

# --- SIDEBAR ---
with st.sidebar:
    st.header("Cấu hình Runtime")
    
    mode = st.selectbox("Mode", ["multi_parent", "single_parent", "multi_flat", "single_flat"], index=0)
    config['MULTI_QUERY_COUNT'] = st.number_input("MULTI_QUERY_COUNT", 1, 5, config.get('MULTI_QUERY_COUNT', 3))
    config['PER_QUERY_CANDIDATES'] = st.number_input("PER_QUERY_CANDIDATES", 1, 50, config.get('PER_QUERY_CANDIDATES', 10))
    config['PARENT_CANDIDATES'] = st.number_input("PARENT_CANDIDATES", 1, 50, config.get('PARENT_CANDIDATES', 10))
    config['FINAL_PARENT_TOP_K'] = st.number_input("FINAL_PARENT_TOP_K", 1, 10, config.get('FINAL_PARENT_TOP_K', 3))
    config['RERANK_MIN_SCORE'] = st.slider("RERANK_MIN_SCORE", 0.0, 1.0, config.get('RERANK_MIN_SCORE', 0.5))
    
    st.text("Strategy cố định: hierarchical")
    has_key = bool(config.get("GEMINI_API_KEY"))
    st.success("Gemini API Key: Sẵn sàng") if has_key else st.error("Gemini API Key: Thiếu")
    
    st.markdown("### Models")
    st.text(f"Embed: {config.get('GEMINI_EMBEDDING_MODEL')}")
    st.text(f"Gen: {config.get('GEMINI_GENERATION_MODEL')}")
    st.text(f"Rerank: {config.get('RERANKER_MODEL')}")
    
    st.markdown("### Status")
    status = get_status('hierarchical')
    store = load_hierarchy_store()
    
    if store:
        st.success("Hierarchy Store: Ready")
        st.text(f"Child count: {len(store['child_map'])}")
        st.text(f"Parent count: {len(store['parent_map'])}")
        amb = sum(1 for p in store['parent_map'].values() if p.get('ambiguous_child_count', 0) > 0)
        st.text(f"Ambiguous: {amb}")
    else:
        st.error("Hierarchy Store: Missing/Stale")
        
    if status['collection_exists']:
        st.success("Collection: Ready")
    else:
        st.error("Collection: Missing")

@st.cache_data
def get_chunks():
    return load_and_validate_chunks()

chunks = get_chunks()

if 'last_result' not in st.session_state:
    st.session_state.last_result = None
if 'last_compare' not in st.session_state:
    st.session_state.last_compare = None

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Ask Advanced RAG", "Query Fan-out", "Parent–Child Explorer", "Mode Comparison", "Evaluation"
])

with tab1:
    question = st.text_area("Nhập câu hỏi pháp lý:")
    if st.button("Hỏi (Run Pipeline)", type="primary"):
        if not store:
            st.error(map_status_to_warning("hierarchy_not_ready")[1])
        else:
            with st.spinner("Đang chạy pipeline..."):
                res = execute_pipeline(question, mode, chunks, config, hierarchy_store=store)
                st.session_state.last_result = res
                
    res = st.session_state.last_result
    if res:
        lvl, msg = map_status_to_warning(res.get('status'))
        if lvl == 'error':
            st.error(msg)
        elif lvl == 'warning':
            st.warning(msg)
            
        if 'answer' in res:
            st.markdown("### Câu trả lời")
            st.info(res['answer'])
            
            st.markdown("### Nguồn trích dẫn (Citations)")
            for c in res['citations']:
                st.markdown(f"- {format_citation(c)}")
                if c.get('warnings'):
                    st.warning(f"Cảnh báo cấu trúc: {c['warnings']}")
                    
        if 'trace' in res:
            st.markdown("### Metrics")
            t = res['trace']
            col1, col2, col3 = st.columns(3)
            col1.metric("Latency (ms)", f"{t.get('total_pipeline_latency_ms', 0):.0f}")
            col2.metric("Gen Calls", t.get('api_calls', {}).get('generation', 0))
            col3.metric("Embed Calls", t.get('api_calls', {}).get('embedding', 0))

with tab2:
    res = st.session_state.last_result
    if res and res.get('mode') in ['multi_flat', 'multi_parent']:
        st.markdown("### Query Variants")
        queries = res.get('trace', {}).get('queries', [])
        
        for q in queries:
            color = "blue" if q.get('origin') == 'original' else "green"
            st.markdown(f"**<span style='color:{color}'>{q['query_id']}</span>**: {q['text']} *(Focus: {q.get('focus')})*", unsafe_allow_html=True)
            
        st.markdown("### Query-Child Matrix")
        if 'parent_aggregation' in res['trace'] or 'multi_query_child_search' in res['trace']:
            # Lấy candidates từ trace của child search
            cands = res['trace'].get('raw_child_hits', [])
            if not cands: # Nếu flat mode
                cands = res.get('candidates', res.get('parent_candidates', [])) 
            mat = build_query_child_matrix(queries, cands)
            if mat:
                st.dataframe(pd.DataFrame(mat), use_container_width=True)
            else:
                st.info("Không có dữ liệu ma trận (Có thể do single mode hoặc lỗi search).")
    else:
        st.info("Chạy chế độ multi_parent hoặc multi_flat ở Tab 1 để xem thông tin Fan-out.")

with tab3:
    res = st.session_state.last_result
    if res and 'parent' in res.get('mode', ''):
        cands = res.get('parent_candidates', [])
        tree = build_parent_tree_data(cands)
        for p in tree:
            with st.expander(f"Parent: {p['parent_id']} ({p['score_text']})"):
                st.markdown(f"**Nguồn:** {p['source']}")
                st.markdown(f"**Rank Movement:** {p['rank_text']}")
                st.markdown("**Supporting Children:**")
                for c in p['supporting_children']:
                    st.markdown(f"- **{c['child_id']}** {'*(Anchor)*' if c['anchor'] else ''} [Queries: {c['query_ids']}]")
                    st.caption(c['snippet'])
    else:
        st.info("Chạy chế độ Parent ở Tab 1 để xem Explorer.")

with tab4:
    st.markdown("### Compare Modes (Retrieval-Only)")
    comp_q = st.text_input("Nhập câu hỏi để so sánh:", key="comp_q")
    if st.button("Chạy So Sánh"):
        if not store:
            st.error("Hierarchy Store missing.")
        else:
            with st.spinner("Đang chạy 4 modes..."):
                rows = []
                for m in ['single_flat', 'multi_flat', 'single_parent', 'multi_parent']:
                    r = execute_pipeline(comp_q, m, chunks, config, hierarchy_store=store, skip_generation=True)
                    # We store raw_child_hits in trace to build matrix in tab2 if needed, but not required here.
                    rows.append(build_compare_row(m, r))
                st.session_state.last_compare = rows
                
    if st.session_state.last_compare:
        st.dataframe(pd.DataFrame(st.session_state.last_compare), use_container_width=True)

with tab5:
    st.markdown("### Evaluation Report")
    st.info("Tính năng đọc Evaluation Report (Không tự động chạy Evaluator).")
    report_file = Path("rag_advanced/buoi_09/reports/eval_results.json")
    if report_file.exists():
        with open(report_file, 'r') as f:
            data = json.load(f)
        st.json(data)
    else:
        st.warning("Chưa có report nào được sinh ra.")
