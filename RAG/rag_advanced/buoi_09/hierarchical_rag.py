import os
import sys
import json
import re
import hashlib
import tempfile
import time
import unicodedata
import math
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

from advanced_rag import hybrid_search

_QUERY_CACHE = {}
import sys
import json
import re
import hashlib
import tempfile
import time
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage" / "hierarchy"
DEFAULT_INPUT_DIR = BASE_DIR.parent.parent / "rag_foundation" / "buoi_05" / "output" / "chunks"

def load_config():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    elif (BASE_DIR / ".env.example").exists():
        load_dotenv(BASE_DIR / ".env.example", override=True)

    config = {}
    
    def get_int(key, min_val, max_val, default):
        val = os.environ.get(key, str(default))
        try:
            val = int(val)
            if not (min_val <= val <= max_val):
                raise ValueError(f"{key} must be between {min_val} and {max_val}")
            return val
        except ValueError as e:
            raise ValueError(f"{key} error: {e}")
            
    def get_float(key, min_val, max_val, default):
        val = os.environ.get(key, str(default))
        try:
            val = float(val)
            if not (min_val <= val <= max_val):
                raise ValueError(f"{key} must be between {min_val} and {max_val}")
            return val
        except ValueError as e:
            raise ValueError(f"{key} error: {e}")

    config['MULTI_QUERY_COUNT'] = get_int('MULTI_QUERY_COUNT', 1, 5, 3)
    config['MULTI_QUERY_MAX_CHARS'] = get_int('MULTI_QUERY_MAX_CHARS', 50, 1000, 300)
    config['MULTI_QUERY_TEMPERATURE'] = get_float('MULTI_QUERY_TEMPERATURE', 0.0, 1.0, 0.2)
    config['MULTI_QUERY_ORIGINAL_WEIGHT'] = get_float('MULTI_QUERY_ORIGINAL_WEIGHT', 0.0, float('inf'), 1.5)
    config['MULTI_QUERY_VARIANT_WEIGHT'] = get_float('MULTI_QUERY_VARIANT_WEIGHT', 0.0, float('inf'), 1.0)
    
    if config['MULTI_QUERY_ORIGINAL_WEIGHT'] == 0.0 and config['MULTI_QUERY_VARIANT_WEIGHT'] == 0.0:
        raise ValueError("MULTI_QUERY_ORIGINAL_WEIGHT and MULTI_QUERY_VARIANT_WEIGHT cannot both be 0")
        
    config['MULTI_QUERY_RRF_K'] = get_int('MULTI_QUERY_RRF_K', 1, 10000, 60)
    config['PER_QUERY_CANDIDATES'] = get_int('PER_QUERY_CANDIDATES', 1, 100, 12)
    config['PARENT_MAX_CHARS'] = get_int('PARENT_MAX_CHARS', 1000, 20000, 6000)
    config['PARENT_SCORE_CHILD_LIMIT'] = get_int('PARENT_SCORE_CHILD_LIMIT', 1, 20, 3)
    config['PARENT_RRF_K'] = get_int('PARENT_RRF_K', 1, 10000, 60)
    config['PARENT_CANDIDATES'] = get_int('PARENT_CANDIDATES', 1, 100, 10)
    config['FINAL_PARENT_TOP_K'] = get_int('FINAL_PARENT_TOP_K', 1, 100, 3)
    
    if config['FINAL_PARENT_TOP_K'] > config['PARENT_CANDIDATES']:
        raise ValueError("FINAL_PARENT_TOP_K must be <= PARENT_CANDIDATES")
        
    config['TOTAL_CONTEXT_MAX_CHARS'] = get_int('TOTAL_CONTEXT_MAX_CHARS', 1000, 100000, 16000)
    if config['TOTAL_CONTEXT_MAX_CHARS'] < config['PARENT_MAX_CHARS']:
        raise ValueError("TOTAL_CONTEXT_MAX_CHARS must be >= PARENT_MAX_CHARS")
        
    config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', '')
    config['GEMINI_EMBEDDING_MODEL'] = os.environ.get('GEMINI_EMBEDDING_MODEL', 'gemini-embedding-2')
    config['GEMINI_GENERATION_MODEL'] = os.environ.get('GEMINI_GENERATION_MODEL', 'gemini-3.5-flash-lite')
    
    if not config['GEMINI_EMBEDDING_MODEL'].strip():
        raise ValueError("GEMINI_EMBEDDING_MODEL cannot be empty")
    if not config['GEMINI_GENERATION_MODEL'].strip():
        raise ValueError("GEMINI_GENERATION_MODEL cannot be empty")
        
    config['RERANKER_MODEL'] = os.environ.get('RERANKER_MODEL', 'BAAI/bge-reranker-v2-m3')
    config['RERANK_MIN_SCORE'] = get_float('RERANK_MIN_SCORE', 0.0, 1.0, 0.5)
    config['RERANK_DEVICE'] = os.environ.get('RERANK_DEVICE', 'auto')
    config['RERANKER_MAX_LENGTH'] = get_int('RERANKER_MAX_LENGTH', 64, 4096, 512)
    config['RERANK_BATCH_SIZE'] = get_int('RERANK_BATCH_SIZE', 1, 64, 4)
        
    return config

def parse_chunk_id(chunk_id):
    parts = chunk_id.split(':')
    try:
        return int(parts[-1])
    except:
        return 0

def get_chunk_numeric_id(chunk_id):
    m = re.search(r':(\d+)$', chunk_id)
    if m:
        return int(m.group(1))
    return 0

def load_and_validate_chunks(input_dir=str(DEFAULT_INPUT_DIR)):
    import glob
    files = glob.glob(os.path.join(input_dir, '*__hierarchical.json'))
    records = []
    seen_ids = set()
    
    for fpath in files:
        with open(fpath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception as e:
                raise ValueError(f"Invalid JSON in {fpath}: {e}")
                
            chunks = data.get('chunks', data) if isinstance(data, dict) else data
            
            for idx, c in enumerate(chunks):
                if c.get('strategy') != 'hierarchical':
                    continue
                    
                for req in ['chunk_id', 'source', 'page_start', 'page_end', 'text']:
                    if req not in c:
                        raise ValueError(f"Missing '{req}' in {fpath} record {idx}")
                
                cid = c['chunk_id']
                if cid in seen_ids:
                    raise ValueError(f"Duplicate chunk_id: {cid} in {fpath} record {idx}")
                seen_ids.add(cid)
                
                if not isinstance(c['page_start'], int) or not isinstance(c['page_end'], int) or c['page_start'] > c['page_end']:
                    raise ValueError(f"Invalid page range in {cid}")
                    
                if not c['text'] or not str(c['text']).strip():
                    raise ValueError(f"Empty text in {cid}")
                    
                struct = c.get('structure')
                if struct is not None and not isinstance(struct, dict):
                    raise ValueError(f"Invalid structure in {cid}")
                    
                records.append(c)
                
    return records

def resolve_hierarchy(chunks):
    # Group by source
    by_source = {}
    for c in chunks:
        by_source.setdefault(c['source'], []).append(c)
        
    resolved_children = []
    
    heading_pattern = re.compile(r'^(Chương\s+[IVXLCDM]+|Điều\s+\d+)', re.IGNORECASE)
    article_pattern = re.compile(r'^Điều\s+\d+', re.IGNORECASE)
    chapter_pattern = re.compile(r'^Chương\s+[IVXLCDM]+', re.IGNORECASE)
    
    for source, src_chunks in by_source.items():
        src_chunks.sort(key=lambda x: get_chunk_numeric_id(x['chunk_id']))
        
        carried_chapter = None
        carried_article = None
        
        for c in src_chunks:
            text = c['text'].strip()
            struct = c.get('structure') or {}
            
            meta_chapter = struct.get('chapter')
            meta_article = struct.get('article')
            meta_clause = struct.get('clause')
            meta_point = struct.get('point')
            
            # Heading matching only at the start
            match = heading_pattern.match(text)
            heading_chapter = None
            heading_article = None
            if match:
                val = match.group(1)
                if val.lower().startswith('chương'):
                    heading_chapter = val
                elif val.lower().startswith('điều'):
                    heading_article = val
                    
            ambiguous = False
            warnings = []
            resolution_method = ""
            
            res_chapter = None
            res_article = None
            
            if meta_chapter or meta_article:
                # Metadata precedence
                resolution_method = "metadata"
                res_chapter = meta_chapter
                res_article = meta_article
                if heading_chapter and heading_chapter != meta_chapter:
                    ambiguous = True
                    warnings.append(f"Metadata chapter '{meta_chapter}' conflicts with inferred heading '{heading_chapter}'")
                if heading_article and heading_article != meta_article:
                    ambiguous = True
                    warnings.append(f"Metadata article '{meta_article}' conflicts with inferred heading '{heading_article}'")
            elif heading_chapter or heading_article:
                resolution_method = "heading_inferred"
                res_chapter = heading_chapter or carried_chapter
                res_article = heading_article
            elif carried_article or carried_chapter:
                resolution_method = "carried_forward"
                res_chapter = carried_chapter
                res_article = carried_article
            else:
                resolution_method = "document_fallback"
                
            # Update carry forward
            if res_chapter: carried_chapter = res_chapter
            if res_article: carried_article = res_article
            
            # Additional ambiguity check: text has "Điều N" in the middle, but metadata doesn't mention it, or we fell back
            # (Though prompt says: "Không coi mọi cụm Điều N xuất hiện giữa một câu là heading" so we just ignore them for heading)
            
            child = {
                "child_id": c['chunk_id'],
                "parent_id": None, # will be set in parent building
                "source": c['source'],
                "page_start": c['page_start'],
                "page_end": c['page_end'],
                "text": c['text'],
                "structural_path": {
                    "chapter": res_chapter,
                    "article": res_article,
                    "clause": meta_clause,
                    "point": meta_point
                },
                "resolution_method": resolution_method,
                "ambiguous": ambiguous,
                "warnings": warnings
            }
            resolved_children.append(child)
            
    return resolved_children

def build_parents(resolved_children, config):
    # Group by (source, article)
    by_article = {}
    for c in resolved_children:
        art = c['structural_path']['article'] or 'document_fallback'
        key = (c['source'], art)
        by_article.setdefault(key, []).append(c)
        
    parents = []
    
    max_chars = config['PARENT_MAX_CHARS']
    
    for (source, art_key), group_children in by_article.items():
        # group_children are already sorted
        
        current_window = []
        current_len = 0
        window_idx = 1
        
        def finalize_window(window, idx):
            text_blocks = [ch['text'] for ch in window]
            joined_text = "\n".join(text_blocks)
            
            p_id = hashlib.sha256(f"{source}_{art_key}_{idx}".encode('utf-8')).hexdigest()[:12]
            
            p_warnings = []
            for ch in window:
                ch['parent_id'] = p_id
                if len(ch['text']) > max_chars and len(window) == 1:
                    p_warnings.append(f"oversized_single_child: {ch['child_id']}")
                    ch['warnings'].append("oversized_single_child")
                    
            parent = {
                "parent_id": p_id,
                "source": source,
                "page_start": min(ch['page_start'] for ch in window),
                "page_end": max(ch['page_end'] for ch in window),
                "article_key": art_key,
                "window_index": idx,
                "child_ids": [ch['child_id'] for ch in window],
                "text": joined_text,
                "char_count": len(joined_text),
                "ambiguous_child_count": sum(1 for ch in window if ch['ambiguous']),
                "warnings": p_warnings
            }
            parents.append(parent)
            
        for ch in group_children:
            ch_len = len(ch['text'])
            # +1 for newline if not first
            add_len = ch_len if not current_window else ch_len + 1
            
            if current_window and current_len + add_len > max_chars:
                finalize_window(current_window, window_idx)
                window_idx += 1
                current_window = [ch]
                current_len = ch_len
            else:
                current_window.append(ch)
                current_len += add_len
                
        if current_window:
            finalize_window(current_window, window_idx)
            
    return parents

def atomic_write(data, dest_path):
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    tmp_path = dest.with_suffix('.tmp')
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, dest)

def get_input_fingerprint(input_dir):
    import glob
    files = sorted(glob.glob(os.path.join(input_dir, '*__hierarchical.json')))
    fingerprints = {}
    for f in files:
        st = os.stat(f)
        fingerprints[os.path.basename(f)] = {
            "size": st.st_size,
            "mtime": st.st_mtime
        }
    return fingerprints

def cmd_audit(args):
    config = load_config()
    print("--- Config Validation Pass ---")
    chunks = load_and_validate_chunks(args.input)
    print(f"Loaded {len(chunks)} valid chunks.")
    
    children = resolve_hierarchy(chunks)
    parents = build_parents(children, config)
    
    ambiguous_count = sum(1 for c in children if c['ambiguous'])
    methods = {}
    for c in children:
        methods[c['resolution_method']] = methods.get(c['resolution_method'], 0) + 1
        
    print(f"\n--- Hierarchy Statistics ---")
    print(f"Total Children: {len(children)}")
    print(f"Total Parents: {len(parents)}")
    print(f"Ambiguous Children: {ambiguous_count}")
    print(f"Resolution Methods: {methods}")
    
    print(f"\n--- Warning Examples ---")
    warned = [c for c in children if c['warnings']]
    for c in warned[:5]:
        print(f"Child {c['child_id']}: {c['warnings']}")
        
    print(f"\n--- Parent Size Distribution ---")
    sizes = [p['char_count'] for p in parents]
    if sizes:
        sizes.sort()
        import statistics
        print(f"Min: {sizes[0]}, Max: {sizes[-1]}, Median: {statistics.median(sizes):.1f}")
    
def cmd_build(args):
    config = load_config()
    chunks = load_and_validate_chunks(args.input)
    children = resolve_hierarchy(chunks)
    parents = build_parents(children, config)
    
    manifest = {
        "schema_version": "1.0",
        "input_fingerprints": get_input_fingerprint(args.input),
        "strategy": "hierarchical",
        "config_identity": {
            "PARENT_MAX_CHARS": config['PARENT_MAX_CHARS']
        },
        "counts": {
            "children": len(children),
            "parents": len(parents)
        },
        "warning_counts": {
            "ambiguous_children": sum(1 for c in children if c['ambiguous']),
            "oversized_parents": sum(1 for p in parents if "oversized_single_child" in "".join(p['warnings']))
        },
        "build_timestamp": time.time()
    }
    
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write(children, STORAGE_DIR / "children.json")
    atomic_write(parents, STORAGE_DIR / "parents.json")
    atomic_write(manifest, STORAGE_DIR / "manifest.json")
    
    print(f"Build successful. Wrote to {STORAGE_DIR}")

def cmd_status(args):
    manifest_file = STORAGE_DIR / "manifest.json"
    if not manifest_file.exists():
        print("Hierarchy store not built (no manifest.json).")
        return
        
    try:
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            
        print("=== HIERARCHY STATUS ===")
        print(f"Schema Version: {manifest.get('schema_version')}")
        print(f"Strategy: {manifest.get('strategy')}")
        print(f"Children count: {manifest.get('counts', {}).get('children')}")
        print(f"Parents count: {manifest.get('counts', {}).get('parents')}")
        print(f"Build timestamp: {manifest.get('build_timestamp')}")
        print(f"Warning counts: {manifest.get('warning_counts')}")
        
    except Exception as e:
        print(f"Error reading manifest: {e}")

def normalize_text(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFC', text.strip())
    text = re.sub(r'\s+', ' ', text)
    return text

def expand_query(question: str, config: dict, query_generator_fn=None):
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")
        
    if len(question) > 2000:
        raise ValueError("Question is too long")
        
    norm_q = normalize_text(question)
    
    model_name = config['GEMINI_GENERATION_MODEL']
    cache_key = hashlib.sha256(f"{norm_q}_{config['MULTI_QUERY_COUNT']}_{config['MULTI_QUERY_TEMPERATURE']}_{model_name}".encode('utf-8')).hexdigest()
    
    if cache_key in _QUERY_CACHE:
        res = dict(_QUERY_CACHE[cache_key])
        res['cache_hit'] = True
        return res
        
    t0 = time.perf_counter()
    
    q0_variant = {
        "query_id": "Q0",
        "text": norm_q,
        "origin": "original",
        "focus": "original_intent"
    }
    
    ref_pattern = re.compile(r'(điều|khoản|điểm|chương|thông tư|nghị định|luật)\s+\d+', re.IGNORECASE)
    has_refs = bool(ref_pattern.search(norm_q))
    
    variants = []
    dropped_duplicate = 0
    
    if config['MULTI_QUERY_COUNT'] > 1:
        req_count = config['MULTI_QUERY_COUNT'] - 1
        
        sys_prompt = (
            f"Bạn là chuyên gia tra cứu pháp luật Việt Nam. Hãy tạo thêm tối đa {req_count} cách diễn đạt "
            "khác cho câu hỏi dưới đây để mở rộng phạm vi tìm kiếm (query expansion). "
            "Yêu cầu:\n"
            "1. Bao phủ các thuật ngữ pháp lý chính xác hoặc đồng nghĩa.\n"
            "2. Đặt trọng tâm vào các khía cạnh khác nhau của câu hỏi gốc.\n"
            "3. Tuyệt đối KHÔNG trả lời câu hỏi.\n"
            "4. KHÔNG thêm sự kiện hoặc bịa ra số Điều/Khoản không có trong câu hỏi gốc.\n"
        )
        if has_refs:
            sys_prompt += "5. BẮT BUỘC giữ nguyên các tham chiếu số Điều/Khoản/văn bản từ câu hỏi gốc trong ít nhất một variant.\n"
            
        user_prompt = f"Câu hỏi gốc: {norm_q}"
        
        try:
            if query_generator_fn:
                generated_queries = query_generator_fn(user_prompt)
            else:
                client = genai.Client(api_key=config['GEMINI_API_KEY'])
                response_schema = types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "queries": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "text": types.Schema(type=types.Type.STRING),
                                    "focus": types.Schema(type=types.Type.STRING)
                                },
                                required=["text", "focus"]
                            )
                        )
                    },
                    required=["queries"]
                )
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_prompt,
                        temperature=config['MULTI_QUERY_TEMPERATURE'],
                        response_mime_type="application/json",
                        response_schema=response_schema
                    )
                )
                
                try:
                    out_dict = json.loads(response.text)
                    generated_queries = out_dict.get('queries', [])
                except Exception:
                    generated_queries = []
                    
        except Exception as e:
            return {
                "original_question": norm_q,
                "queries": [q0_variant],
                "model": model_name,
                "generation_latency_ms": (time.perf_counter() - t0) * 1000,
                "status": "query_generation_unavailable",
                "error": str(e),
                "cache_hit": False,
                "dropped_duplicate_count": 0
            }
                
        seen_texts = {norm_q.casefold()}
        
        for g in generated_queries:
            raw_text = g.get('text', '')
            norm_g = normalize_text(raw_text)
            case_g = norm_g.casefold()
            
            if not norm_g or len(norm_g) > config['MULTI_QUERY_MAX_CHARS']:
                continue
                
            if case_g in seen_texts:
                dropped_duplicate += 1
                continue
                
            g_refs = set(re.findall(r'điều\s+\d+', case_g))
            q_refs = set(re.findall(r'điều\s+\d+', norm_q.casefold()))
            if g_refs - q_refs:
                continue
                
            seen_texts.add(case_g)
            
            variants.append({
                "query_id": None,
                "text": norm_g,
                "origin": "generated",
                "focus": g.get('focus', 'paraphrase')
            })
            
            if len(variants) >= req_count:
                break
                
    final_queries = [q0_variant]
    for i, v in enumerate(variants, start=1):
        v['query_id'] = f"Q{i}"
        final_queries.append(v)
        
    result = {
        "original_question": norm_q,
        "queries": final_queries,
        "model": model_name,
        "generation_latency_ms": (time.perf_counter() - t0) * 1000,
        "status": "ready",
        "cache_hit": False,
        "dropped_duplicate_count": dropped_duplicate
    }
    
    _QUERY_CACHE[cache_key] = dict(result)
    return result

def cmd_expand_query(args):
    config = load_config()
    print(f"Expanding query: '{args.question}'")
    result = expand_query(args.question, config)
    
    print("\n=== QUERY EXPANSION RESULT ===")
    print(f"Status: {result['status']}")
    print(f"Model: {result['model']}")
    print(f"Latency: {result['generation_latency_ms']:.2f} ms")
    print(f"Cache Hit: {result['cache_hit']}")
    print(f"Dropped Duplicates: {result.get('dropped_duplicate_count', 0)}")
    if 'error' in result:
        print(f"Error: {result['error']}")
        
    print("\n--- QUERIES ---")
    for q in result['queries']:
        print(f"[{q['query_id']}] ({q['origin']}) Focus: {q['focus']}")
        print(f"Text: {q['text']}\n")

def multi_query_child_search(question: str, strategy: str, chunks: list, config: dict, expand_fn=None, hybrid_fn=None):
    if expand_fn is None:
        expand_fn = expand_query
    if hybrid_fn is None:
        hybrid_fn = hybrid_search
        
    t0 = time.perf_counter()
    
    # 1. Expand query
    expand_res = expand_fn(question, config)
    queries = expand_res.get('queries', [])
    q_status = expand_res.get('status')
    
    q0 = next((q for q in queries if q['query_id'] == 'Q0'), None)
    if not q0:
        raise ValueError("Critical Error: Q0 missing from expanded queries")
        
    # 2. Per-query Retrieval
    trace = {
        "queries_requested": config['MULTI_QUERY_COUNT'],
        "queries_valid": len(queries),
        "queries_executed": 0,
        "queries_failed": 0,
        "expansion_latency_ms": expand_res.get('generation_latency_ms', 0),
        "retrieval_latency_ms": {},
        "result_count_per_query": {},
        "union_child_count": 0,
        "overlap_distribution": {},
        "fusion_latency_ms": 0.0,
        "gemini_expansion_calls": 0 if expand_res.get('cache_hit') else 1,
        "semantic_embedding_calls": 0 # updated below
    }
    
    per_query_results = {}
    q_errors = {}
    
    for q in queries:
        qid = q['query_id']
        t_ret_start = time.perf_counter()
        try:
            res = hybrid_fn(q['text'], strategy, chunks)
            trace['semantic_embedding_calls'] += 1 # hybrid_search calls semantic embedding once
            cands = res['candidates'][:config['PER_QUERY_CANDIDATES']]
            per_query_results[qid] = cands
            trace['queries_executed'] += 1
            trace['result_count_per_query'][qid] = len(cands)
        except Exception as e:
            q_errors[qid] = str(e)
            trace['queries_failed'] += 1
        trace['retrieval_latency_ms'][qid] = (time.perf_counter() - t_ret_start) * 1000
        
    if 'Q0' in q_errors:
        return {
            "status": "multi_query_failed",
            "candidates": [],
            "error": f"Q0 retrieval failed: {q_errors['Q0']}",
            "trace": trace
        }
        
    status = "multi_query_partial" if q_errors else "multi_query_success"
    
    # 3. Cross-query RRF Fusion
    t_fusion_start = time.perf_counter()
    union_map = {}
    
    mq_k = config['MULTI_QUERY_RRF_K']
    w_orig = config['MULTI_QUERY_ORIGINAL_WEIGHT']
    w_var = config['MULTI_QUERY_VARIANT_WEIGHT']
    
    for q in queries:
        qid = q['query_id']
        if qid not in per_query_results:
            continue
            
        weight = w_orig if q['origin'] == 'original' else w_var
        
        for cand in per_query_results[qid]:
            cid = cand['chunk_id']
            inner_rank = cand.get('fused_rank') # From inner RRF
            if inner_rank is None:
                # Fallback if mock returns something else
                inner_rank = 1
                
            if cid not in union_map:
                union_map[cid] = {
                    "child_id": cid,
                    "text": cand['text'],
                    "source": cand['source'],
                    "page_start": cand['page_start'],
                    "page_end": cand['page_end'],
                    "multi_query_rrf_score": 0.0,
                    "support_query_count": 0,
                    "support_query_ids": [],
                    "per_query_ranks": {},
                    "per_query_trace": {}
                }
            else:
                existing = union_map[cid]
                # Metadata check
                if existing['text'] != cand['text'] or existing['source'] != cand['source']:
                    raise ValueError(f"Metadata mismatch for child_id {cid}")
                    
            entry = union_map[cid]
            entry['multi_query_rrf_score'] += weight / (mq_k + inner_rank)
            entry['support_query_count'] += 1
            entry['support_query_ids'].append(qid)
            entry['per_query_ranks'][qid] = inner_rank
            entry['per_query_trace'][qid] = cand
            
    trace['union_child_count'] = len(union_map)
    
    # Overlap distribution
    overlap_counts = {}
    for entry in union_map.values():
        c = entry['support_query_count']
        overlap_counts[str(c)] = overlap_counts.get(str(c), 0) + 1
    trace['overlap_distribution'] = overlap_counts
    
    # 4. Sort and assign rank
    fused_list = list(union_map.values())
    for entry in fused_list:
        entry['best_query_rank'] = min(entry['per_query_ranks'].values())
        entry['support_query_ids'].sort(key=lambda x: 0 if x == 'Q0' else int(x[1:]))
        
    fused_list.sort(key=lambda d: (
        -d['multi_query_rrf_score'],
        -d['support_query_count'],
        d['best_query_rank'],
        d['child_id']
    ))
    
    for i, data in enumerate(fused_list, start=1):
        data['multi_query_rank'] = i
        
    trace['fusion_latency_ms'] = (time.perf_counter() - t_fusion_start) * 1000
    trace['total_latency_ms'] = (time.perf_counter() - t0) * 1000
    
    return {
        "status": status,
        "candidates": fused_list,
        "trace": trace,
        "warnings": [f"{qid} failed: {err}" for qid, err in q_errors.items()],
        "queries": queries
    }

def cmd_multi_child(args):
    config = load_config()
    print(f"Executing Multi-Query Child Search for: '{args.question}'")
    
    # Load chunks
    chunks = load_and_validate_chunks()
    
    try:
        res = multi_query_child_search(args.question, 'hierarchical', chunks, config)
    except Exception as e:
        print(f"Error during search: {e}")
        return
        
    print(f"\n=== STATUS: {res['status']} ===")
    
    if res.get('warnings'):
        print("\n--- WARNINGS ---")
        for w in res['warnings']:
            print(w)
            
    print("\n--- QUERIES ---")
    for q in res.get('queries', []):
        print(f"[{q['query_id']}] ({q['origin']}): {q['text']}")
        
    print("\n--- TOP CHILD HITS ---")
    print(f"{'Rank':<5} | {'Child ID':<30} | {'MQ-RRF':<8} | {'Supp':<5} | {'BestRank':<8} | {'Q_IDs'}")
    print("-" * 85)
    for c in res['candidates'][:20]: # show top 20
        mq_score = f"{c['multi_query_rrf_score']:.4f}"
        q_ids = ",".join(c['support_query_ids'])
        print(f"{c['multi_query_rank']:<5} | {c['child_id']:<30} | {mq_score:<8} | {c['support_query_count']:<5} | {c['best_query_rank']:<8} | {q_ids}")
        
    print("\n--- TRACE ---")
    print(json.dumps(res['trace'], indent=2))

def load_hierarchy_store():
    manifest_file = STORAGE_DIR / "manifest.json"
    children_file = STORAGE_DIR / "children.json"
    parents_file = STORAGE_DIR / "parents.json"
    
    if not (manifest_file.exists() and children_file.exists() and parents_file.exists()):
        return None
        
    try:
        with open(children_file, 'r', encoding='utf-8') as f:
            children = json.load(f)
        with open(parents_file, 'r', encoding='utf-8') as f:
            parents = json.load(f)
            
        child_map = {c['child_id']: c for c in children}
        parent_map = {p['parent_id']: p for p in parents}
        return {"child_map": child_map, "parent_map": parent_map}
    except Exception:
        return None

def parent_retrieve(question: str, mode: str, chunks: list, config: dict, expand_fn=None, hybrid_fn=None, hierarchy_store=None):
    if hierarchy_store is None:
        hierarchy_store = load_hierarchy_store()
        
    if not hierarchy_store:
        return {"status": "hierarchy_not_ready", "candidates": [], "trace": {}}
        
    child_map = hierarchy_store['child_map']
    parent_map = hierarchy_store['parent_map']
    
    original_mq_count = config['MULTI_QUERY_COUNT']
    if mode == 'single_parent':
        config['MULTI_QUERY_COUNT'] = 1
        
    child_res = multi_query_child_search(question, 'hierarchical', chunks, config, expand_fn, hybrid_fn)
    
    config['MULTI_QUERY_COUNT'] = original_mq_count
    
    if child_res['status'] == 'multi_query_failed':
        return child_res
        
    child_hits = child_res['candidates']
    trace = child_res['trace']
    
    t0 = time.perf_counter()
    
    parent_groups = {}
    child_chars = 0
    
    for ch in child_hits:
        cid = ch['child_id']
        child_chars += len(ch['text'])
        
        if cid not in child_map:
            raise ValueError(f"Child {cid} not found in hierarchy registry")
            
        pid = child_map[cid]['parent_id']
        if pid not in parent_map:
            raise ValueError(f"Parent {pid} not found for child {cid}")
            
        parent_groups.setdefault(pid, []).append(ch)
        
    aggregated_parents = []
    limit = config['PARENT_SCORE_CHILD_LIMIT']
    k = config['PARENT_RRF_K']
    
    for pid, hits in parent_groups.items():
        hits.sort(key=lambda x: x['multi_query_rank'])
        
        scoring_hits = hits[:limit]
        p_score = 0.0
        for h in scoring_hits:
            p_score += 1.0 / (k + h['multi_query_rank'])
            
        supp_q_ids = set()
        for h in hits:
            supp_q_ids.update(h['support_query_ids'])
            
        p_doc = parent_map[pid]
        
        struct_path = child_map[hits[0]['child_id']]['structural_path']
        
        aggregated_parents.append({
            "parent_id": pid,
            "source": p_doc['source'],
            "page_start": p_doc['page_start'],
            "page_end": p_doc['page_end'],
            "structural_path": struct_path,
            "text": p_doc['text'],
            "parent_rrf_score": p_score,
            "parent_rank": 0,
            "anchor_child_id": hits[0]['child_id'],
            "scoring_child_ids": [h['child_id'] for h in scoring_hits],
            "supporting_child_ids": [h['child_id'] for h in hits],
            "support_query_ids": sorted(list(supp_q_ids), key=lambda x: 0 if x=='Q0' else int(x[1:])),
            "best_child_rank": hits[0]['multi_query_rank'],
            "ambiguous": p_doc.get('ambiguous_child_count', 0) > 0,
            "warnings": p_doc.get('warnings', []),
            "_hits": hits
        })
        
    aggregated_parents.sort(key=lambda x: (
        -x['parent_rrf_score'],
        -len(x['support_query_ids']),
        x['best_child_rank'],
        x['parent_id']
    ))
    
    dropped_by_candidate_limit = max(0, len(aggregated_parents) - config['PARENT_CANDIDATES'])
    aggregated_parents = aggregated_parents[:config['PARENT_CANDIDATES']]
    
    final_parents = []
    current_chars = 0
    dropped_by_budget = 0
    max_budget = config['TOTAL_CONTEXT_MAX_CHARS']
    
    for idx, p in enumerate(aggregated_parents):
        p_len = len(p['text'])
        if current_chars + p_len > max_budget:
            if idx == 0:
                p['warnings'].append("first_parent_exceeds_budget")
                final_parents.append(p)
                current_chars += p_len
            else:
                dropped_by_budget += 1
        else:
            final_parents.append(p)
            current_chars += p_len
            
    for i, p in enumerate(final_parents, 1):
        p['parent_rank'] = i
        
    p_trace = {
        "input_child_hit_count": len(child_hits),
        "unique_parent_count": len(parent_groups),
        "child_counts_per_parent": {pid: len(hits) for pid, hits in parent_groups.items()},
        "parents_dropped_by_limit": dropped_by_candidate_limit,
        "parents_dropped_by_budget": dropped_by_budget,
        "child_chars": child_chars,
        "expanded_parent_chars": current_chars,
        "expansion_factor": current_chars / child_chars if child_chars > 0 else 0.0,
        "ambiguous_parents": sum(1 for p in final_parents if p['ambiguous']),
        "mapping_latency_ms": (time.perf_counter() - t0) * 1000
    }
    trace['parent_aggregation'] = p_trace
    trace['total_latency_ms'] = (time.perf_counter() - t0) * 1000 + trace.get('total_latency_ms', 0)
    
    return {
        "status": child_res.get('status', 'success'),
        "candidates": final_parents,
        "trace": trace,
        "queries": child_res.get('queries', [])
    }

def cmd_parent_retrieve(args):
    config = load_config()
    print(f"Executing Parent Retrieve for: '{args.question}' (Mode: {args.mode})")
    
    chunks = load_and_validate_chunks()
    
    try:
        res = parent_retrieve(args.question, args.mode, chunks, config)
    except Exception as e:
        print(f"Error during search: {e}")
        return
        
    print(f"\n=== STATUS: {res['status']} ===")
    if res['status'] == 'hierarchy_not_ready':
        print("Hierarchy store missing or stale.")
        return
        
    print("\n--- MAPPING TREE ---")
    for p in res['candidates']:
        score = f"{p['parent_rrf_score']:.4f}"
        print(f"Parent [{p['parent_rank']}]: {p['parent_id']} (Score: {score}, Anchor: {p['anchor_child_id']})")
        if p['warnings']:
            print(f"  └── Warnings: {p['warnings']}")
        for h in p['_hits']:
            support_type = "Scoring" if h['child_id'] in p['scoring_child_ids'] else "Supporting"
            q_ids = ",".join(h['support_query_ids'])
            print(f"  └── Child ({support_type}): {h['child_id']} (MQ Rank: {h['multi_query_rank']}, Qs: {q_ids})")
        print()
        
    print("--- TRACE ---")
    print(json.dumps(res['trace']['parent_aggregation'], indent=2))

def execute_pipeline(question: str, mode: str, chunks: list, config: dict, 
                     expand_fn=None, hybrid_fn=None, rerank_fn=None, generation_fn=None, hierarchy_store=None, skip_generation=False):
                     
    t_start = time.perf_counter()
    api_calls = {"embedding": 0, "generation": 0}
    trace = {}
    
    if mode in ['single_flat', 'multi_flat']:
        old = config['MULTI_QUERY_COUNT']
        if mode == 'single_flat':
            config['MULTI_QUERY_COUNT'] = 1
        res = multi_query_child_search(question, 'hierarchical', chunks, config, expand_fn, hybrid_fn)
        config['MULTI_QUERY_COUNT'] = old
        
        if 'success' not in res['status'] and 'partial' not in res['status']:
            return res
        trace.update(res['trace'])
        candidates = []
        for c in res['candidates']:
            candidates.append({
                "parent_id": c['child_id'],
                "anchor_child_id": c['child_id'],
                "supporting_child_ids": [c['child_id']],
                "source": c['source'],
                "page_start": c['page_start'],
                "page_end": c['page_end'],
                "structural_path": {},
                "text": c['text'],
                "parent_rank": c['multi_query_rank'],
                "warnings": []
            })
    else:
        res = parent_retrieve(question, mode, chunks, config, expand_fn, hybrid_fn, hierarchy_store)
        if 'success' not in res['status'] and 'partial' not in res['status']:
            return res
        trace.update(res['trace'])
        candidates = res['candidates']
        
    if not candidates:
        return {"status": "insufficient_evidence", "trace": trace}
        
    t_rerank = time.perf_counter()
    k_rerank = config['PARENT_CANDIDATES']
    cands_to_rerank = candidates[:k_rerank]
    
    if rerank_fn:
        scores = rerank_fn(question, [c['text'] for c in cands_to_rerank])
    else:
        try:
            import torch
            from advanced_rag import get_reranker
            (model, device), tokenizer = get_reranker(config)
            pairs = [[question, c['text']] for c in cands_to_rerank]
            scores = []
            with torch.no_grad():
                batch_size = config['RERANK_BATCH_SIZE']
                for i in range(0, len(pairs), batch_size):
                    batch_pairs = pairs[i:i+batch_size]
                    inputs = tokenizer(batch_pairs, padding=True, truncation=True, max_length=config['RERANKER_MAX_LENGTH'], return_tensors='pt')
                    inputs = {k: v.to(device) for k, v in inputs.items()}
                    outputs = model(**inputs)
                    logits = outputs.logits.view(-1).cpu().tolist()
                    if isinstance(logits, float): logits = [logits]
                    scores.extend(logits)
        except Exception as e:
            return {"status": "reranker_unavailable", "error": str(e), "trace": trace}
            
    for c, logit in zip(cands_to_rerank, scores):
        c['parent_rerank_raw_score'] = logit
        try:
            c['parent_rerank_score'] = 1.0 / (1.0 + math.exp(-logit))
        except OverflowError:
            c['parent_rerank_score'] = 0.0 if logit < 0 else 1.0
            
    cands_to_rerank.sort(key=lambda d: (-d['parent_rerank_score'], d['parent_rank'], d['parent_id']))
    
    for i, c in enumerate(cands_to_rerank, 1):
        c['parent_rerank_rank'] = i
        c['parent_rank_change'] = c['parent_rank'] - i
        
    accepted_evidence = []
    final_k = config['FINAL_PARENT_TOP_K']
    min_score = config.get('RERANK_MIN_SCORE', 0.5)
    
    for c in cands_to_rerank[:final_k]:
        if c['parent_rerank_score'] >= min_score:
            accepted_evidence.append(c)
            
    trace['rerank_latency_ms'] = (time.perf_counter() - t_rerank) * 1000
    trace['accepted_evidence_count'] = len(accepted_evidence)
    
    if not accepted_evidence:
        return {"status": "insufficient_evidence", "trace": trace, "candidates": cands_to_rerank}
        
    if skip_generation:
        return {
            "status": "success",
            "mode": mode,
            "parent_candidates": cands_to_rerank,
            "accepted_evidence": accepted_evidence,
            "trace": trace
        }
        
    t_gen = time.perf_counter()
    prompt = f"Câu hỏi gốc: {question}\n\nEvidence:\n"
    citations = []
    
    for i, ev in enumerate(accepted_evidence, 1):
        ev_id = f"P{i}"
        prompt += f"[{ev_id}]\n{ev['text']}\n\n"
        citations.append({
            "evidence_id": ev_id,
            "parent_id": ev['parent_id'],
            "anchor_child_id": ev.get('anchor_child_id'),
            "supporting_child_ids": ev.get('supporting_child_ids', []),
            "source": ev['source'],
            "page_start": ev['page_start'],
            "page_end": ev['page_end'],
            "structural_path": ev.get('structural_path', {}),
            "parent_rerank_score": ev['parent_rerank_score'],
            "ambiguous": ev.get('ambiguous', False),
            "warnings": ev.get('warnings', [])
        })
        
    prompt += "Trả lời câu hỏi hoàn toàn dựa vào evidence trên. Trích dẫn [P1], [P2] vào mỗi câu nhận định."
    
    if generation_fn:
        answer = generation_fn(prompt)
    else:
        try:
            client = genai.Client(api_key=config['GEMINI_API_KEY'])
            resp = client.models.generate_content(
                model=config['GEMINI_GENERATION_MODEL'],
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0)
            )
            answer = resp.text
            api_calls['generation'] += 1
        except Exception as e:
            return {"status": "generation_failed", "error": str(e), "trace": trace}
            
    trace['generation_latency_ms'] = (time.perf_counter() - t_gen) * 1000
    trace['total_pipeline_latency_ms'] = (time.perf_counter() - t_start) * 1000
    
    if 'gemini_expansion_calls' in trace:
        api_calls['generation'] += trace['gemini_expansion_calls']
    if 'semantic_embedding_calls' in trace:
        api_calls['embedding'] += trace['semantic_embedding_calls']
        
    trace['api_calls'] = api_calls
    
    return {
        "status": "success",
        "mode": mode,
        "original_question": question,
        "parent_candidates": cands_to_rerank,
        "accepted_evidence": accepted_evidence,
        "answer": answer,
        "citations": citations,
        "trace": trace
    }

def cmd_query(args):
    config = load_config()
    chunks = load_and_validate_chunks()
    print(f"Executing Full Pipeline (Mode: {args.mode}) for: '{args.question}'")
    
    res = execute_pipeline(args.question, args.mode, chunks, config)
    print(f"\nSTATUS: {res['status']}")
    if res['status'] == 'success':
        print("\n=== ANSWER ===")
        print(res['answer'])
        print("\n=== CITATIONS ===")
        for c in res['citations']:
            print(f"[{c['evidence_id']}] {c['parent_id']} (Score: {c['parent_rerank_score']:.4f})")
        print("\n=== TRACE ===")
        print(json.dumps(res['trace'], indent=2))
    elif 'error' in res:
        print(res['error'])
        
def cmd_compare(args):
    config = load_config()
    chunks = load_and_validate_chunks()
    store = load_hierarchy_store()
    
    modes = ['single_flat', 'multi_flat', 'single_parent', 'multi_parent']
    for m in modes:
        print(f"\n>>> Running Mode: {m}")
        res = execute_pipeline(args.question, m, chunks, config, hierarchy_store=store, skip_generation=True)
        if res['status'] == 'success':
            print(f"Accepted Evidence: {len(res['accepted_evidence'])}")
            for e in res['accepted_evidence']:
                print(f"  - {e['parent_id']} (Rerank: {e['parent_rerank_score']:.4f}, Rank Change: {e['parent_rank_change']})")
        else:
            print(f"Status: {res['status']}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')
    
    audit_parser = subparsers.add_parser('hierarchy-audit')
    audit_parser.add_argument('--input', default=str(DEFAULT_INPUT_DIR))
    
    build_parser = subparsers.add_parser('build-hierarchy')
    build_parser.add_argument('--input', default=str(DEFAULT_INPUT_DIR))
    
    status_parser = subparsers.add_parser('hierarchy-status')
    
    expand_parser = subparsers.add_parser('expand-query')
    expand_parser.add_argument('--question', required=True)
    
    mc_parser = subparsers.add_parser('multi-child')
    mc_parser.add_argument('--question', required=True)
    
    pr_parser = subparsers.add_parser('parent-retrieve')
    pr_parser.add_argument('--question', required=True)
    pr_parser.add_argument('--mode', choices=['single_parent', 'multi_parent'], default='multi_parent')
    
    query_parser = subparsers.add_parser('query')
    query_parser.add_argument('--question', required=True)
    query_parser.add_argument('--mode', choices=['single_parent', 'multi_parent', 'single_flat', 'multi_flat'], default='multi_parent')
    
    comp_parser = subparsers.add_parser('compare')
    comp_parser.add_argument('--question', required=True)
    
    eval_parser = subparsers.add_parser('evaluate')
    
    args = parser.parse_args()
    
    if args.command == 'hierarchy-audit':
        cmd_audit(args)
    elif args.command == 'build-hierarchy':
        cmd_build(args)
    elif args.command == 'hierarchy-status':
        cmd_status(args)
    elif args.command == 'expand-query':
        cmd_expand_query(args)
    elif args.command == 'multi-child':
        cmd_multi_child(args)
    elif args.command == 'parent-retrieve':
        cmd_parent_retrieve(args)
    elif args.command == 'query':
        cmd_query(args)
    elif args.command == 'compare':
        cmd_compare(args)
    elif args.command == 'evaluate':
        from evaluate import cmd_evaluate
        cmd_evaluate(args)
    else:
        parser.print_help()
