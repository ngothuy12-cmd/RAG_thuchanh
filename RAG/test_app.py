import sys
from pathlib import Path
sys.path.append(str(Path("rag_advanced/buoi_08").resolve()))
from advanced_rag import query_pipeline
res = query_pipeline("Điều 7 quy định gì?", "hierarchical", "hybrid_rerank")
print(res['status'])
print(res.get('warnings', []))
