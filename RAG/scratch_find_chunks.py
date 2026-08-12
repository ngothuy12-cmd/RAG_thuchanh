import json
import sys

def find(keyword, file):
    with open(file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    for c in chunks:
        if keyword.lower() in c['text'].lower():
            print(f"File: {file} - ID: {c['chunk_id']} - Text: {c['text'][:100]}")

files = [
    "rag_foundation/buoi_05/output/chunks/TT_02_2023_NHNN__hierarchical.json",
    "rag_foundation/buoi_05/output/chunks/TT_06_2023_NHNN__hierarchical.json"
]

find("điều 7", files[0])
find("phân loại nợ", files[0])
