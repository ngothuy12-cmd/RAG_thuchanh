import sys
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Add buoi_14 directory to sys.path to enable src imports
buoi14_dir = os.path.dirname(os.path.abspath(__file__))
if buoi14_dir not in sys.path:
    sys.path.insert(0, buoi14_dir)

from src.config import ROLES, ROLE_HIERARCHY, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
from src.secure_retriever import SecureRetriever, is_role_allowed

# Streamlit Page Config
st.set_page_config(
    page_title="RAG Secure Search — RBAC Buổi 15",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS styling for premium security-focused UI
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0d47a1;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #424242;
        margin-bottom: 1.5rem;
    }
    .result-card {
        background-color: #ffffff;
        border-left: 5px solid #1976d2;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .badge-rank {
        background-color: #e3f2fd;
        color: #0d47a1;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-method {
        background-color: #f3e5f5;
        color: #4a148c;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-roles {
        background-color: #fff3e0;
        color: #e65100;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #ffe0b2;
    }
    .filter-banner {
        background-color: #e8f5e9;
        border: 1px solid #a5d6a7;
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        margin-bottom: 1rem;
        color: #1b5e20;
    }
    .blocked-banner {
        background-color: #fff8e1;
        border: 1px solid #ffe082;
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        margin-bottom: 1rem;
        color: #e65100;
    }
    .graph-box {
        background-color: #f1f8e9;
        border: 1px solid #c5e1a5;
        border-radius: 8px;
        padding: 1rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_secure_retriever():
    """Cache the SecureRetriever instance to avoid re-loading models on every rerun."""
    return SecureRetriever()


def check_neo4j_secure_graph_hints(doc_ids: list, chunk_ids: list, user_roles: list):
    """
    Queries Neo4j for 1-hop legal relationships and NEXT chunk chains
    with explicit access filtering by user_roles.
    """
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session(database=NEO4J_DATABASE) as session:
            # Secure Query for 1-hop VanBan legal relationships
            cypher_doc_rel = """
            MATCH (v1:VanBan)-[r]->(v2:VanBan)
            WHERE (v1.id IN $doc_ids OR v2.id IN $doc_ids)
              AND type(r) IN ['SUA_DOI_BO_SUNG', 'CAN_CU', 'THAY_THE', 'VAN_BAN_BO_SUNG', 'HOP_NHAT']
              AND any(role IN v1.allowed_roles WHERE role IN $user_roles)
              AND any(role IN v2.allowed_roles WHERE role IN $user_roles)
            RETURN v1.so_ky_hieu AS SourceDoc, type(r) AS RelType, v2.so_ky_hieu AS TargetDoc
            LIMIT 10
            """
            res_doc = session.run(cypher_doc_rel, doc_ids=[str(d) for d in doc_ids], user_roles=user_roles)
            doc_rels = [
                f"{r['SourceDoc']} ==[{r['RelType']}]==> {r['TargetDoc']}"
                for r in res_doc
            ]
            
            # Secure Query for 1-hop NEXT chunk chains
            cypher_chunk_next = """
            MATCH (d1:DieuKhoan)-[r:NEXT]->(d2:DieuKhoan)
            WHERE d1.id IN $chunk_ids
              AND any(role IN d1.allowed_roles WHERE role IN $user_roles)
              AND any(role IN d2.allowed_roles WHERE role IN $user_roles)
            RETURN d1.id AS CurrentChunk, d1.article AS CurrentArticle, d2.id AS NextChunk, d2.article AS NextArticle
            LIMIT 10
            """
            res_chunk = session.run(cypher_chunk_next, chunk_ids=[str(c) for c in chunk_ids], user_roles=user_roles)
            chunk_next = [
                f"`{r['CurrentChunk']}` ({r['CurrentArticle']}) ──[:NEXT]──> `{r['NextChunk']}` ({r['NextArticle']})"
                for r in res_chunk
            ]
            
        driver.close()
        return True, doc_rels, chunk_next, None
    except Exception as e:
        return False, [], [], str(e)


def main():
    st.markdown('<div class="main-title">🛡️ RAG Secure Search — Buổi 15</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Cài đặt Kiểm soát Truy cập dựa trên Vai trò (RBAC) ở mức Dữ liệu và Retrieval Pipeline</div>', unsafe_allow_html=True)

    # Initialize retriever
    with st.spinner("Đang khởi tạo Secure Retriever Pipeline & các mô hình AI..."):
        retriever = load_secure_retriever()

    # Sidebar Options
    with st.sidebar:
        st.header("⚙️ Cấu Hình Retrieval & RBAC")
        
        # 1. Select Roles (RBAC User Impersonation)
        st.subheader("👤 Vai trò của bạn (Your Roles)")
        selected_roles = st.multiselect(
            "Chọn vai trò người dùng hiện tại:",
            options=ROLES,
            default=["Guest"],
            help="Hệ thống sẽ lọc bỏ 100% tài liệu không có quyền truy cập ứng với các vai trò được chọn ở đây."
        )
        
        if not selected_roles:
            st.warning("⚠️ Vui lòng chọn ít nhất 1 vai trò để thực hiện truy vấn.")
            return
            
        st.markdown(f"**Vai trò đang chọn:** `{'`, `'.join(selected_roles)}`")
        
        st.markdown("---")
        
        # 2. Select Retrieval Method
        method_map = {
            "Hybrid + Rerank (Khuyên dùng)": "hybrid_rerank",
            "Hybrid (BM25 + Dense)": "hybrid",
            "Dense Search (Vector)": "dense",
            "BM25 Search (Từ khóa)": "bm25",
            "Graph Search (Neo4j Cypher)": "graph"
        }
        selected_method_name = st.selectbox(
            "Phương pháp Retrieval:",
            options=list(method_map.keys()),
            index=0
        )
        method_code = method_map[selected_method_name]
        
        top_k = st.slider("Số lượng Top-k kết quả:", min_value=1, max_value=15, value=5)
        candidate_k = st.slider("Candidate Pool (k cho Hybrid/Rerank):", min_value=5, max_value=30, value=20)
        
        st.markdown("---")
        st.markdown("### 🔒 Nguyên tắc Bảo mật RBAC:")
        st.markdown("""
        - **Property-based Access Control**: Gán thẻ `allowed_roles` vào từng Node dữ liệu.
        - **Zero Data Leakage**: Lọc bỏ văn bản bị cấm **TRƯỚC** khi đưa sang CrossEncoder Reranker.
        - **Secure Cypher Query**: Lọc trực tiếp ở tầng đồ thị Neo4j bằng câu lệnh `WHERE any(role IN node.allowed_roles WHERE role IN $user_roles)`.
        """)

    # Quick Sample Queries for testing RBAC
    st.markdown("##### 💡 Câu hỏi mẫu thử nghiệm RBAC:")
    sample_col1, sample_col2, sample_col3 = st.columns(3)
    
    question_input = ""
    with sample_col1:
        if st.button("📋 1. Mức HR (Lương thưởng / Kỷ luật)", use_container_width=True):
            question_input = "Xử lý khi làm mất lộ bí mật chìa khóa kho tiền két sắt và quy định kỷ luật nhân sự"
    with sample_col2:
        if st.button("📊 2. Mức Risk (Tín dụng / Quản trị)", use_container_width=True):
            question_input = "Tỷ lệ an toàn vốn và quản lý rủi ro dự trữ ngoại hối"
    with sample_col3:
        if st.button("🌐 3. Mức Public (Đóng gói tiền / Quy trình)", use_container_width=True):
            question_input = "Điều kiện đóng gói tiền mặt và thành lập quỹ tín dụng nhân dân"

    # Search Input Bar
    default_q = "Quy định về bảo mật chìa khóa kho tiền, két sắt và xử lý kỷ luật nhân sự"
    user_query = st.text_input(
        "Nhập câu hỏi tra cứu:", 
        value=question_input if question_input else default_q,
        placeholder="Nhập câu hỏi cần tìm kiếm..."
    )
    
    btn_col, _ = st.columns([1, 4])
    with btn_col:
        search_clicked = st.button("🔍 Thực hiện Tìm kiếm An toàn", type="primary", use_container_width=True)

    if search_clicked or user_query:
        st.markdown("---")
        st.markdown(f"### 📋 KẾT QUẢ TÌM KIẾM AN TOÀN (`{selected_method_name}` | User Roles: `{' + '.join(selected_roles)}`)")

        with st.spinner("Đang thực hiện truy vấn và lọc quyền bảo mật..."):
            # 1. Fetch Secure Results
            results = retriever.retrieve(
                question=user_query,
                user_roles=selected_roles,
                method=method_code,
                top_k=top_k
            )

            # 2. Compute Filtered-out count statistic for transparency
            # Run query as Admin (unrestricted) to find total potential matches
            admin_results = retriever.retrieve(
                question=user_query,
                user_roles=["Admin"],
                method=method_code,
                top_k=20
            )
            
            # Count how many Admin top candidates are blocked for current selected_roles
            blocked_count = 0
            for item in admin_results:
                if not is_role_allowed(item.get("allowed_roles", []), selected_roles):
                    blocked_count += 1

        # Display Filter Status Banner
        if blocked_count > 0:
            st.markdown(
                f'<div class="blocked-banner">🛡️ <b>RBAC Security Audit:</b> Đã tự động lọc bỏ <b>{blocked_count}</b> kết quả nhạy cảm khỏi danh sách trả về do vai trò <code>{selected_roles}</code> không đủ quyền truy cập.</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="filter-banner">✅ <b>RBAC Security Clear:</b> Tất cả {len(results)} kết quả trả về đều hợp lệ và được cấp quyền truy cập cho vai trò <code>{selected_roles}</code>.</div>',
                unsafe_allow_html=True
            )

        if not results:
            st.warning("⚠️ Không tìm thấy kết quả nào phù hợp thuộc phạm vi truy cập của bạn.")
            return

        # Display Result Cards
        for res in results:
            allowed_roles_str = ", ".join(res.get("allowed_roles", []))
            
            with st.container():
                st.markdown(f"""
                <div class="result-card">
                    <div>
                        <span class="badge-rank">Rank #{res['rank']}</span>
                        <span class="badge-method">{res['retrieval_method'].upper()}</span>
                        <span class="badge-roles">🔒 Quyền xem: [{allowed_roles_str}]</span>
                        <span style="float: right; font-weight: bold; color: #1565c0;">Score: {res['score']}</span>
                    </div>
                    <div style="margin-top: 10px; font-weight: 600; color: #0d47a1; font-size: 1.05rem;">
                        📌 {res['citation']}
                    </div>
                    <div style="margin-top: 4px; font-size: 0.85rem; color: #666;">
                        Document ID: <code>{res['document_id']}</code> | Chunk ID: <code>{res['chunk_id']}</code>
                    </div>
                    <div style="margin-top: 10px; font-size: 0.95rem; line-height: 1.5; color: #212121; background-color: #fafafa; padding: 10px; border-radius: 4px;">
                        {res['text']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Rerank & Access Audit Comparison Table (For Hybrid Rerank mode)
        if method_code == "hybrid_rerank":
            with st.expander("🔍 Chi tiết Lọc Bảo mật Rerank (Admin vs User Roles Audit Table)", expanded=False):
                audit_rows = []
                for idx, cand in enumerate(admin_results, 1):
                    allowed = is_role_allowed(cand.get("allowed_roles", []), selected_roles)
                    status_str = "✅ PERMITTED" if allowed else "⛔ BLOCKED (Data Leakage Prevented)"
                    audit_rows.append({
                        "Unrestricted Rank": idx,
                        "Chunk ID": cand["chunk_id"],
                        "Allowed Roles": cand["allowed_roles"],
                        "Access Status": status_str,
                        "Citation": cand["citation"]
                    })
                st.dataframe(pd.DataFrame(audit_rows), use_container_width=True)

        # Graph Hints Section (Secure Neo4j Graph Filtering)
        st.markdown("---")
        st.markdown("### 🌐 Secure Graph Hints (Thông tin Đồ thị Phân quyền)")
        
        retrieved_doc_ids = list(dict.fromkeys([res["document_id"] for res in results]))
        retrieved_chunk_ids = [res["chunk_id"] for res in results]
        
        is_neo4j_ok, doc_rels, chunk_next, err_msg = check_neo4j_secure_graph_hints(
            retrieved_doc_ids, 
            retrieved_chunk_ids, 
            user_roles=selected_roles
        )
        
        if is_neo4j_ok:
            st.success(f"✅ Đồ thị Neo4j sẵn sàng! Đã áp dụng câu lệnh Cypher lọc theo quyền `user_roles = {selected_roles}`.")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("**1. Quan hệ pháp lý 1-hop (Đã lọc quyền):**")
                if doc_rels:
                    for r in doc_rels:
                        st.markdown(f"- `{r}`")
                else:
                    st.info("Không có quan hệ pháp lý liên văn bản trực tiếp 1-hop thuộc thẩm quyền của bạn.")
            with col_g2:
                st.markdown("**2. Chuỗi điều khoản kế cận NEXT 1-hop (Đã lọc quyền):**")
                if chunk_next:
                    for cn in chunk_next:
                        st.markdown(f"- {cn}")
                else:
                    st.info("Không tìm thấy chuỗi NEXT điều khoản thuộc thẩm quyền của bạn.")
        else:
            st.warning("⚠️ Kết nối Neo4j tạm thời gián đoạn. Retrieval vector/lexical vẫn bảo mật bình thường.")
            st.caption(f"Thông báo lỗi: {err_msg}")


if __name__ == "__main__":
    main()
