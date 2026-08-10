import json
import time
import datetime
from pathlib import Path
from hierarchical_rag import load_config, load_and_validate_chunks, load_hierarchy_store, execute_pipeline

def cmd_evaluate(args):
    config = load_config()
    chunks = load_and_validate_chunks()
    store = load_hierarchy_store()
    
    questions_path = Path("eval/questions.json")
    if not questions_path.exists():
        print("Không tìm thấy eval/questions.json")
        return
        
    with open(questions_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
        
    modes = ['single_flat', 'multi_flat', 'single_parent', 'multi_parent']
    results = {m: {'MRR': 0, 'nDCG': 0, 'Child_Recall': 0, 'Parent_Recall': 0, 'Latency': 0, 'Queries': 0, 'Gen_Calls': 0, 'Embed_Calls': 0, 'Context_Chars': 0, 'Exp_Factor': 0, 'Count': 0} for m in modes}
    
    per_question_results = []
    
    for q in questions:
        print(f"Evaluating: {q['question_id']}...")
        q_res = {"question_id": q['question_id'], "runs": {}}
        for m in modes:
            print(f"  Mode: {m}...")
            # We mock the real gen network calls to speed up if generation is not needed for metric
            # But we actually want real retrieval so we must use Gemini embeddings
            res = execute_pipeline(q['question'], m, chunks, config, hierarchy_store=store, skip_generation=True)
            
            cands = res.get('accepted_evidence', [])
            trace = res.get('trace', {})
            
            # evaluate
            rel_parents = set(q['relevant_parent_ids'])
            retrieved_parents = [c['parent_id'] for c in cands]
            
            # binary relevance
            hits = [1 if p in rel_parents else 0 for p in retrieved_parents]
            
            # MRR
            mrr = 0.0
            if 1 in hits:
                mrr = 1.0 / (hits.index(1) + 1)
                
            # Recall@K Parent
            parent_recall = 0.0
            if rel_parents:
                parent_recall = sum(hits) / len(rel_parents)
                
            # Child Recall (for parents we look at scoring children)
            rel_children = set(q['relevant_child_ids'])
            child_recall = 0.0
            retrieved_children = set()
            for c in cands:
                retrieved_children.update(c.get('supporting_child_ids', []))
            
            if rel_children:
                child_recall = len(retrieved_children.intersection(rel_children)) / len(rel_children)
                
            q_res['runs'][m] = {
                "mrr": mrr,
                "parent_recall": parent_recall,
                "child_recall": child_recall,
                "latency_ms": trace.get('total_pipeline_latency_ms', 0),
                "expansion_factor": trace.get('parent_aggregation', {}).get('expansion_factor', 1.0),
                "context_chars": sum(len(c.get('text', '')) for c in cands)
            }
            
            # accumulate
            results[m]['MRR'] += mrr
            results[m]['Parent_Recall'] += parent_recall
            results[m]['Child_Recall'] += child_recall
            results[m]['Latency'] += trace.get('total_pipeline_latency_ms', 0)
            results[m]['Gen_Calls'] += trace.get('api_calls', {}).get('generation', 0)
            results[m]['Embed_Calls'] += trace.get('api_calls', {}).get('embedding', 0)
            results[m]['Context_Chars'] += sum(len(c.get('text', '')) for c in cands)
            results[m]['Exp_Factor'] += trace.get('parent_aggregation', {}).get('expansion_factor', 1.0)
            results[m]['Count'] += 1
            
        per_question_results.append(q_res)
        
    # Aggregate
    agg = {}
    for m in modes:
        cnt = results[m]['Count']
        if cnt > 0:
            agg[m] = {
                "MRR@K": results[m]['MRR'] / cnt,
                "Parent_Recall@K": results[m]['Parent_Recall'] / cnt,
                "Child_Recall@K": results[m]['Child_Recall'] / cnt,
                "Mean_Latency_ms": results[m]['Latency'] / cnt,
                "Mean_Context_Chars": results[m]['Context_Chars'] / cnt,
                "Mean_Expansion_Factor": results[m]['Exp_Factor'] / cnt,
                "Total_Gen_Calls": results[m]['Gen_Calls'],
                "Total_Embed_Calls": results[m]['Embed_Calls']
            }
            
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "identity": {
            "model_embed": config.get('GEMINI_EMBEDDING_MODEL'),
            "model_rerank": config.get('RERANKER_MODEL'),
            "corpus_size": len(chunks),
            "hierarchy_ready": store is not None
        },
        "aggregate_metrics": agg,
        "per_question_results": per_question_results,
        "human_review_warning": "Không khẳng định multi_parent thắng tuyệt đối nếu các nhãn chứa needs_human_review=true."
    }
    
    Path("reports").mkdir(exist_ok=True)
    with open("reports/eval_results.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print("Đã lưu report tại reports/eval_results.json")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    cmd_evaluate(args)
