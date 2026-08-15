import os
import re
import pandas as pd
from bs4 import BeautifulSoup


def prepare_corpus():
    # Base paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    buoi14_dir = os.path.dirname(script_dir)
    source_dir = os.path.abspath(os.path.join(buoi14_dir, "..", "kb+hops"))
    
    metadata_path = os.path.join(source_dir, "metadata.csv")
    content_path = os.path.join(source_dir, "content.csv")
    
    output_dir = os.path.join(buoi14_dir, "data", "processed")
    os.makedirs(output_dir, exist_ok=True)
    output_csv = os.path.join(output_dir, "chunks_normalized.csv")
    
    print(f"Reading source metadata from: {metadata_path}")
    print(f"Reading source content from: {content_path}")
    
    # Read source CSVs directly without altering originals
    df_meta = pd.read_csv(metadata_path, encoding="utf-8").set_index("id")
    df_content = pd.read_csv(content_path, encoding="utf-8")
    
    chunks = []
    
    for _, row in df_content.iterrows():
        doc_id = str(row["id"])
        html_content = row["content_html"]
        
        # Get metadata for doc_id if available
        meta = df_meta.loc[doc_id].to_dict() if doc_id in df_meta.index else {}
        
        # Parse HTML to clean text
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator="\n")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        
        curr_chapter = ""
        curr_section = ""
        curr_article = ""
        curr_lines = []
        chunk_idx = 0
        
        def add_chunk_record(art_name, chap_name, sec_name, lines_buf, c_count):
            txt = "\n".join(lines_buf).strip()
            if not txt:
                return c_count
            
            # Form clean heading context if article title was captured
            full_text = txt
            if art_name and not txt.startswith(art_name):
                full_text = f"{art_name}\n{txt}"
            
            c_id = f"{doc_id}_chk_{c_count:04d}"
            
            chunks.append({
                "chunk_id": c_id,
                "document_id": doc_id,
                "text": full_text,
                "source_file": "content.csv",
                "title": str(meta.get("title", "")),
                "so_ky_hieu": str(meta.get("so_ky_hieu", "")),
                "document_type": str(meta.get("loai_van_ban", "")),
                "chapter": chap_name,
                "section": sec_name,
                "article": art_name,
                "clause": "",
                "effective_date": str(meta.get("ngay_co_hieu_luc", meta.get("ngay_ban_hanh", ""))),
                "status": str(meta.get("tinh_trang_hieu_luc", "")),
                "co_quan_ban_hanh": str(meta.get("co_quan_ban_hanh", ""))
            })
            return c_count + 1

        for line in lines:
            if re.match(r"^Chương\s+[I|V|X|L|C|D|M|\d]+", line, re.IGNORECASE):
                curr_chapter = line
            elif re.match(r"^Mục\s+\d+", line, re.IGNORECASE):
                curr_section = line
            elif re.match(r"^Điều\s+\d+", line, re.IGNORECASE):
                if curr_lines:
                    chunk_idx = add_chunk_record(curr_article or "Lời mở đầu / Căn cứ", curr_chapter, curr_section, curr_lines, chunk_idx)
                    curr_lines = []
                curr_article = line
            else:
                curr_lines.append(line)
                
        if curr_lines:
            add_chunk_record(curr_article or "Lời mở đầu / Căn cứ", curr_chapter, curr_section, curr_lines, chunk_idx)

    df_chunks = pd.DataFrame(chunks)
    
    # Save output to buoi_14/data/processed/chunks_normalized.csv
    df_chunks.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"\nSaved normalized chunks to: {output_csv}")
    
    # Metrics
    total_chunks = len(df_chunks)
    total_docs = df_chunks["document_id"].nunique()
    missing_text = df_chunks["text"].isnull().sum() + (df_chunks["text"].str.strip() == "").sum()
    duplicate_chunks = df_chunks["chunk_id"].duplicated().sum()
    
    print("\n" + "="*50)
    print("CORPUS PREPARATION SUMMARY")
    print("="*50)
    print(f"Total chunks: {total_chunks}")
    print(f"Number of documents: {total_docs}")
    print(f"Missing text count: {missing_text}")
    print(f"Duplicate chunk_id count: {duplicate_chunks}")
    print("="*50)
    
    print("\n3 SAMPLE RECORDS:")
    for idx, r in enumerate(df_chunks.head(3).to_dict(orient="records"), 1):
        print(f"\n--- Sample {idx} ---")
        print(f"chunk_id: {r['chunk_id']}")
        print(f"document_id: {r['document_id']}")
        print(f"title: {r['title'][:80]}...")
        print(f"so_ky_hieu: {r['so_ky_hieu']}")
        print(f"article: {r['article']}")
        print(f"text (first 200 chars):\n{r['text'][:200]}...")

if __name__ == "__main__":
    prepare_corpus()
