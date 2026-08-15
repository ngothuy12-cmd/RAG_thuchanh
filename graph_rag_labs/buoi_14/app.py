import sys
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Add buoi_14 directory to sys.path to enable src imports
buoi14_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(buoi14_dir)
if buoi14_dir not in sys.path:
    sys.path.insert(0, buoi14_dir)

from src.unified_retriever import UnifiedRetriever

# Streamlit Page Config
st.set_page_config(
    page_title="RAG Hybrid Search — Buổi 14",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS styling for premium look
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 1.5rem;
    }
    .result-card {
        background-color: #f8f9fa;
        border-left: 5px solid #1E88E5;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    .badge {
        background-color: #E3F2FD;
        color: #0D47A1;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .graph-box {
        background-color: #F1F8E9;
        border: 1px solid #AED581;
        border-radius: 6px;
        padding: 1rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_retriever():
    """Cache the UnifiedRetriever instance to avoid re-loading models on every rerun."""
    return UnifiedRetriever()


def check_neo4j_graph_hints(doc_ids: list, chunk_ids: list):
    """
    Checks Neo4j for direct 1-hop legal relationships and NEXT chunk chains.
    """
    env_path = os.path.join(root_dir, ".env")
    load_dotenv(env_path)
    
    uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    user = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
    password = os.getenv("NEO4J_PASSWORD", "abcd1234")
    db = os.getenv("NEO4J_DATABASE", "neo4j")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session(database=db) as session:
            # Query 1-hop VanBan legal relationships
            cypher_doc_rel = """
            MATCH (v1:VanBan {lab_session: 'buoi_14'})-[r]->(v2:VanBan {lab_session: 'buoi_14'})
            WHERE v1.id IN $doc_ids OR v2.id IN $doc_ids
              AND type(r) IN ['SUA_DOI_BO_SUNG', 'CAN_CU', 'THAY_THE', 'VAN_BAN_BO_SUNG', 'HOP_NHAT']
            RETURN v1.so_ky_hieu AS SourceDoc, type(r) AS RelType, v2.so_ky_hieu AS TargetDoc
            LIMIT 10
            """
            res_doc = session.run(cypher_doc_rel, doc_ids=[str(d) for d in doc_ids])
            doc_rels = [
                f"{r['SourceDoc']} ==[{r['RelType']}]==> {r['TargetDoc']}"
                for r in res_doc
            ]
            
            # Query 1-hop NEXT chunk chains
            cypher_chunk_next = """
            MATCH (d1:DieuKhoan {lab_session: 'buoi_14'})-[r:NEXT]->(d2:DieuKhoan {lab_session: 'buoi_14'})
            WHERE d1.id IN $chunk_ids
            RETURN d1.id AS CurrentChunk, d1.article AS CurrentArticle, d2.id AS NextChunk, d2.article AS NextArticle
            LIMIT 10
            """
            res_chunk = session.run(cypher_chunk_next, chunk_ids=[str(c) for c in chunk_ids])
            chunk_next = [
                f"`{r['CurrentChunk']}` ({r['CurrentArticle']}) ──[:NEXT]──> `{r['NextChunk']}` ({r['NextArticle']})"
                for r in res_chunk
            ]
            
        driver.close()
        return True, doc_rels, chunk_next, None
    except Exception as e:
        return False, [], [], str(e)


def main():
    st.markdown('<div class="main-title">RAG Hybrid Search — Buổi 14</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Nâng cấp Retrieval với BM25, Dense (Bi-Encoder), Hybrid (RRF) & CrossEncoder Reranking</div>', unsafe_allow_html=True)

    # Sidebar Options
    with st.sidebar:
        st.header("⚙️ Cấu Hình Retrieval")
        
        method_map = {
            "BM25": "bm25",
            "Dense": "dense",
            "Hybrid": "hybrid",
            "Hybrid + Rerank": "hybrid_rerank"
        }
        selected_method_name = st.selectbox(
            "Phương pháp Retrieval:",
            options=list(method_map.keys()),
            index=3  # Default to Hybrid + Rerank
        )
        method_code = method_map[selected_method_name]
        
        top_k = st.slider("Số lượng Top-k trả về:", min_value=1, max_value=15, value=5)
        
        st.markdown("---")
        st.markdown("### 📌 Hướng dẫn sử dụng:")
        st.markdown("""
        - **BM25:** Lexical search khớp từ khóa chính xác (số hiệu, mã điều khoản).
        - **Dense:** Vector search bằng Bi-Encoder tiếng Việt (`bkai-foundation-models`).
        - **Hybrid:** Hợp nhất BM25 + Dense bằng thuật toán Reciprocal Rank Fusion (RRF).
        - **Hybrid + Rerank:** Tái xếp hạng Top candidates bằng CrossEncoder (`mmarco-mMiniLMv2`).
        """)

    # Load retriever model
    with st.spinner("Đang khởi tạo các mô hình Retrieval (BM25, Bi-Encoder, CrossEncoder)..."):
        retriever = load_retriever()

    # Search Input Bar
    default_question = "Theo Nghị định 73/2016/NĐ-CP thì điều kiện cấp giấy phép hoạt động doanh nghiệp bảo hiểm gồm những gì?"
    question_input = st.text_input("Câu hỏi:", value=default_question, placeholder="Nhập câu hỏi cần tra cứu...")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        search_button = st.button("🔍 Tìm kiếm", type="primary", use_container_width=True)

    if search_button or question_input:
        st.markdown(f"### 📋 Kết Quả Tìm Kiếm (`{selected_method_name}` | Top-{top_k})")
        
        # Execute unified retrieval
        with st.spinner("Đang truy vấn dữ liệu..."):
            results = retriever.retrieve(question=question_input, method=method_code, top_k=top_k)
            
        if not results:
            st.warning("Không tìm thấy kết quả phù hợp.")
            return

        # If method is hybrid_rerank, display BEFORE vs AFTER RERANK comparison table
        if method_code == "hybrid_rerank":
            with st.expander("📊 Bảng so sánh thứ hạng BEFORE RERANK vs AFTER RERANK", expanded=True):
                candidates_before = retriever.hybrid.search(question_input, top_k=20, candidate_k=20)
                
                # Build comparison dataframe
                comp_rows = []
                for res in results:
                    cid = res["chunk_id"]
                    before_hit = next((c for c in candidates_before if c["chunk_id"] == cid), None)
                    comp_rows.append({
                        "After Rerank Rank": res["rank"],
                        "Chunk ID": cid,
                        "Rerank Score": res["rerank_score"],
                        "Before Rerank Rank (Hybrid)": before_hit["final_rank"] if before_hit else "N/A",
                        "RRF Score": res["hybrid_score"],
                        "Citation": res["citation"]
                    })
                st.dataframe(pd.DataFrame(comp_rows), use_container_width=True)

        # Display result cards
        for res in results:
            with st.container():
                st.markdown(f"""
                <div class="result-card">
                    <div>
                        <span class="badge">Rank #{res['rank']}</span>
                        <span class="badge">Method: {res['retrieval_method'].upper()}</span>
                        <span style="margin-left: 10px; font-weight: bold;">Score: {res['score']}</span>
                    </div>
                    <div style="margin-top: 8px; font-weight: 600; color: #0D47A1;">
                        📌 {res['citation']}
                    </div>
                    <div style="margin-top: 4px; font-size: 0.85rem; color: #666;">
                        Document ID: <code>{res['document_id']}</code> | Chunk ID: <code>{res['chunk_id']}</code>
                    </div>
                    <div style="margin-top: 10px; font-size: 0.95rem; line-height: 1.5;">
                        {res['text']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Graph Hints Section
        st.markdown("---")
        st.markdown("### 🌐 Graph Hints (Thông tin Đồ thị Bổ trợ)")
        
        retrieved_doc_ids = list(dict.fromkeys([res["document_id"] for res in results]))
        retrieved_chunk_ids = [res["chunk_id"] for res in results]
        
        st.markdown(f"- **Retrieved Document IDs:** `{retrieved_doc_ids}`")
        st.markdown(f"- **Retrieved Chunk IDs:** `{retrieved_chunk_ids}`")
        
        is_neo4j_ok, doc_rels, chunk_next, err_msg = check_neo4j_graph_hints(retrieved_doc_ids, retrieved_chunk_ids)
        
        if is_neo4j_ok:
            st.success("✅ Kết nối Neo4j sẵn sàng!")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("**1. Quan hệ pháp lý liên văn bản (1-hop):**")
                if doc_rels:
                    for r in doc_rels:
                        st.markdown(f"- `{r}`")
                else:
                    st.info("Không có quan hệ pháp lý liên văn bản trực tiếp 1-hop trong tập kết quả này.")
            with col_g2:
                st.markdown("**2. Chuỗi điều khoản kế cận (1-hop NEXT):**")
                if chunk_next:
                    for cn in chunk_next:
                        st.markdown(f"- {cn}")
                else:
                    st.info("Không tìm thấy chuỗi NEXT điều khoản kế cận.")
        else:
            st.warning("⚠️ Neo4j chưa sẵn sàng (Chế độ Standalone). Retrieval vẫn hoạt động bình thường.")
            st.caption(f"Chi tiết thông báo: {err_msg}")


if __name__ == "__main__":
    main()
