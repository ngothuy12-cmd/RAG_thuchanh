def format_citation(cite: dict) -> str:
    src = cite.get('source', '')
    p_start = cite.get('page_start', '')
    p_end = cite.get('page_end', '')
    page_str = f"p.{p_start}-{p_end}" if p_start == p_end else f"p.{p_start}-{p_end}"
    score = f"{cite.get('parent_rerank_score', 0):.2f}"
    return f"[{cite.get('evidence_id')}] Nguồn: {src} ({page_str}) - Rerank Score: {score}"

def build_query_child_matrix(queries, candidates) -> list:
    matrix = []
    q_ids = [q['query_id'] for q in queries]
    
    for c in candidates:
        row = {
            "Child ID": c.get('child_id', c.get('parent_id', 'Unknown')),
            "Support Count": c.get('support_query_count', len(c.get('support_query_ids', []))),
            "MQ-RRF Score": f"{c.get('multi_query_rrf_score', c.get('parent_rank', 0)):.4f}"
        }
        
        per_query_ranks = c.get('per_query_ranks', {})
        for q_id in q_ids:
            row[q_id] = per_query_ranks.get(q_id, "—")
            
        matrix.append(row)
    return matrix

def build_parent_tree_data(parent_cands) -> list:
    tree = []
    for p in parent_cands:
        node = {
            "parent_id": p['parent_id'],
            "source": f"{p['source']} p.{p['page_start']}-{p['page_end']}",
            "rank_text": f"MQ Rank: {p['parent_rank']} -> Rerank Rank: {p.get('parent_rerank_rank', 'N/A')}",
            "score_text": f"MQ Score: {p.get('parent_rrf_score', 0):.4f} -> Rerank Score: {p.get('parent_rerank_score', 0):.4f}",
            "supporting_children": []
        }
        
        # Build children list if _hits exists
        for h in p.get('_hits', []):
            q_ids = ",".join(h.get('support_query_ids', []))
            node['supporting_children'].append({
                "child_id": h['child_id'],
                "query_ids": q_ids,
                "anchor": h['child_id'] == p.get('anchor_child_id'),
                "snippet": h.get('text', '')[:100] + "..."
            })
        tree.append(node)
    return tree

def map_status_to_warning(status: str) -> tuple[str, str]:
    mapping = {
        'hierarchy_not_ready': ('error', 'Hierarchy chưa sẵn sàng. Vui lòng Build Hierarchy.'),
        'collection_not_ready': ('error', 'Semantic Collection chưa sẵn sàng. Vui lòng Prepare Semantic.'),
        'query_generation_unavailable': ('error', 'Lỗi sinh Query Variants (Gemini). Hãy kiểm tra API Key.'),
        'multi_query_partial': ('warning', 'Có lỗi ở một số Query Variants. Kết quả có thể không đầy đủ.'),
        'reranker_unavailable': ('error', 'Reranker Model lỗi hoặc chưa tải được.'),
        'insufficient_evidence': ('warning', 'Không có evidence nào qua được cửa kiểm duyệt (Rerank Score quá thấp).'),
        'generation_failed': ('error', 'Lỗi sinh Answer (Gemini).'),
        'success': ('success', 'Thành công')
    }
    return mapping.get(status, ('error', f'Lỗi không xác định: {status}'))

def build_compare_row(mode: str, result: dict) -> dict:
    if result.get('status') not in ['success', 'insufficient_evidence']:
        return {
            "Mode": mode,
            "Status": result.get('status'),
            "Warnings": map_status_to_warning(result.get('status'))[1]
        }
        
    cands = result.get('accepted_evidence', [])
    trace = result.get('trace', {})
    
    unique_sources = set(c['source'] for c in cands)
    unique_articles = set(c['parent_id'] for c in cands)
    
    agg = trace.get('parent_aggregation', {})
    child_chars = agg.get('child_chars', 0)
    exp_chars = agg.get('expanded_parent_chars', sum(len(c.get('text','')) for c in cands))
    
    return {
        "Mode": mode,
        "Status": result.get('status'),
        "Final Evidence IDs": ", ".join(c['parent_id'] for c in cands),
        "Unit Type": "Parent" if 'parent' in mode else "Child",
        "Unique Sources": len(unique_sources),
        "Unique Articles": len(unique_articles),
        "Retrieved Child Count": trace.get('input_child_hit_count', len(result.get('parent_candidates', []))),
        "Expanded Parent Count": len(cands),
        "Context Chars": exp_chars,
        "Expansion Factor": f"{agg.get('expansion_factor', 1.0):.2f}x",
        "Latency (ms)": f"{trace.get('total_pipeline_latency_ms', 0):.0f}",
        "Gen Calls": trace.get('api_calls', {}).get('generation', 0),
        "Embed Calls": trace.get('api_calls', {}).get('embedding', 0),
        "Warnings": len(cands[0].get('warnings', [])) if cands and cands[0].get('warnings') else 0
    }
