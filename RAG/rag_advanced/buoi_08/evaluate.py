import argparse
import json
import time
import math
from pathlib import Path
import sys

# Import functions from advanced_rag
# adding current dir to sys.path just in case
sys.path.append(str(Path(__file__).resolve().parent))
from advanced_rag import query_pipeline

BASE_DIR = Path(__file__).resolve().parent

def dcg_at_k(r, k):
    r = r[:k]
    if not r:
        return 0.
    return r[0] + sum(r[i] / math.log2(i + 2) for i in range(1, len(r)))

def ndcg_at_k(r, k):
    # For binary relevance, ideal r is [1, 1, ..., 1] (up to total relevant or k)
    dcg_max = dcg_at_k(sorted(r, reverse=True), k)
    if not dcg_max:
        return 0.
    return dcg_at_k(r, k) / dcg_max

def recall_at_k(r, k, relevant_count):
    if relevant_count == 0:
        return 0.
    return sum(r[:k]) / relevant_count

def mrr_at_k(r, k):
    for i, rel in enumerate(r[:k]):
        if rel:
            return 1.0 / (i + 1)
    return 0.0

def evaluate_mode(questions, strategy, mode, k):
    recalls = []
    mrrs = []
    ndcgs = []
    latencies = []
    
    for q_data in questions:
        q = q_data['question']
        gold_chunks = set(q_data['relevant_chunk_ids'])
        
        t0 = time.perf_counter()
        try:
            res = query_pipeline(q, strategy, mode, fake_gen=lambda x: "")
        except Exception as e:
            raise RuntimeError(f"Lỗi khi đánh giá query '{q}': {e}")
            
        latency = (time.perf_counter() - t0) * 1000
        latencies.append(latency)
        
        retrieved = [c['chunk_id'] for c in res.get('evidence', [])][:k]
        
        r = [1 if cid in gold_chunks else 0 for cid in retrieved]
        
        recalls.append(recall_at_k(r, k, len(gold_chunks)))
        mrrs.append(mrr_at_k(r, k))
        
        ideal_r = [1] * min(len(gold_chunks), k)
        ndcg_val = 0.0
        if ideal_r:
            ndcg_val = dcg_at_k(r, k) / dcg_at_k(ideal_r, k)
        ndcgs.append(ndcg_val)
        
    latencies.sort()
    p50 = latencies[len(latencies)//2] if latencies else 0.0
    mean_lat = sum(latencies)/len(latencies) if latencies else 0.0
    
    return {
        "mode": mode,
        "k": k,
        "Recall@K": sum(recalls)/len(recalls) if recalls else 0.0,
        "MRR@K": sum(mrrs)/len(mrrs) if mrrs else 0.0,
        "nDCG@K": sum(ndcgs)/len(ndcgs) if ndcgs else 0.0,
        "latency_mean_ms": mean_lat,
        "latency_p50_ms": p50
    }

def cmd_evaluate(args):
    q_path = BASE_DIR / "eval" / "questions.json"
    if not q_path.exists():
        print("Lỗi: Không tìm thấy eval/questions.json")
        return
        
    with open(q_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
        
    needs_review = any(q.get('needs_human_review', False) for q in questions)

    
    if needs_review:
        print("WARNING: Bộ câu hỏi gold còn ở trạng thái needs_human_review=true. Kết quả này KHÔNG tuyên bố mode chiến thắng chính thức.")
        
    modes = ['bm25', 'semantic', 'hybrid', 'hybrid_rerank']
    report = {
        "timestamp": time.time(),
        "strategy": args.strategy,
        "k": args.k,
        "needs_human_review": needs_review,
        "results": {}
    }
    
    print(f"Bắt đầu đánh giá (K={args.k})")
    for m in modes:
        print(f"Đang chạy {m}...")
        try:
            res = evaluate_mode(questions, args.strategy, m, args.k)
            report["results"][m] = res
        except Exception as e:
            print(f"Lỗi khi đánh giá {m}: {e}")
            report["results"][m] = {"error": str(e)}
            
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / "eval_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print(f"\nĐã lưu report tại: {report_file}")
    
    print(f"\n{'Mode':<15} | {'Recall':<8} | {'MRR':<8} | {'nDCG':<8} | {'p50 (ms)':<8}")
    print("-" * 55)
    for m in modes:
        r = report["results"].get(m, {})
        if "error" in r:
            print(f"{m:<15} | LỖI: {r['error']}")
        else:
            print(f"{m:<15} | {r['Recall@K']:<8.4f} | {r['MRR@K']:<8.4f} | {r['nDCG@K']:<8.4f} | {r['latency_p50_ms']:<8.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="hierarchical")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    cmd_evaluate(args)
