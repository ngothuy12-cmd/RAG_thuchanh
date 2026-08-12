import os
import json
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).parent.resolve()
CHUNKS_DIR = BASE_DIR.parent / "buoi_05" / "output" / "chunks"
LOCAL_DB = BASE_DIR / "local.db"
CHROMA_DIR = BASE_DIR / "storage" / "chroma"
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE, override=True)

def get_db_connection():
    try:
        import psycopg
        conn = psycopg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            dbname=os.getenv("POSTGRES_DB", "rag_db"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "")
        )
        return conn, "postgres"
    except Exception:
        conn = sqlite3.connect(str(LOCAL_DB))
        return conn, "sqlite"

def init_db():
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    if db_type == "postgres":
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                text TEXT NOT NULL
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                text TEXT NOT NULL
            )
        """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

def get_gemini_client():
    key = os.getenv("GEMINI_API_KEY", "")
    if key:
        try:
            return genai.Client(api_key=key)
        except Exception as e:
            print(f"Lỗi khởi tạo Gemini Client: {e}")
    return None

def get_chroma_collection():
    try:
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        return chroma_client.get_or_create_collection(name="rag_collection")
    except Exception:
        return None

def index():
    collection = get_chroma_collection()
    if not collection:
        return "ChromaDB chưa sẵn sàng."
        
    if not CHUNKS_DIR.exists():
        return f"Thư mục chunks không tồn tại: {CHUNKS_DIR}"
        
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    
    docs_to_db = []
    
    for filename in os.listdir(CHUNKS_DIR):
        if filename.endswith(".json"):
            filepath = CHUNKS_DIR / filename
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    chunk_id = item.get("chunk_id", "")
                    text = item.get("text", "")
                    if not chunk_id or not text:
                        continue
                    
                    embedding = None
                    gemini_client = get_gemini_client()
                    if gemini_client:
                        try:
                            res = gemini_client.models.embed_content(
                                model='gemini-embedding-2',
                                contents=text,
                                config=types.EmbedContentConfig(output_dimensionality=384)
                            )
                            embedding = res.embeddings[0].values
                        except Exception as e:
                            print(f"Lỗi tính embedding ({chunk_id}): {e}")
                    
                    if embedding:
                        try:
                            collection.upsert(
                                embeddings=[embedding],
                                documents=[text],
                                ids=[chunk_id]
                            )
                        except Exception:
                            pass
                    else:
                        try:
                            collection.upsert(
                                documents=[text],
                                ids=[chunk_id]
                            )
                        except Exception:
                            pass
                        
                    docs_to_db.append((chunk_id, text))
    
    for doc in docs_to_db:
        try:
            if db_type == "postgres":
                cur.execute("INSERT INTO chunks (chunk_id, text) VALUES (%s, %s) ON CONFLICT (chunk_id) DO NOTHING", doc)
            else:
                cur.execute("INSERT OR IGNORE INTO chunks (chunk_id, text) VALUES (?, ?)", doc)
        except Exception:
            pass
            
    conn.commit()
    cur.close()
    conn.close()
    return f"Quá trình index hoàn tất. Đã xử lý {len(docs_to_db)} chunks."

def ask(question: str, k: int = 3):
    collection = get_chroma_collection()
    if not collection:
        return [], "Lỗi: ChromaDB không hoạt động."
        
    q_embedding = None
    gemini_client = get_gemini_client()
    if gemini_client:
        try:
            res = gemini_client.models.embed_content(
                model='gemini-embedding-2',
                contents=question,
                config=types.EmbedContentConfig(output_dimensionality=384)
            )
            q_embedding = res.embeddings[0].values
        except Exception as e:
            print(f"Lỗi tạo embedding câu hỏi (sẽ dùng Chroma fallback): {e}")
            q_embedding = None
    
    if q_embedding:
        try:
            results = collection.query(
                query_embeddings=[q_embedding],
                n_results=k
            )
        except Exception as e:
            return [], f"Lỗi tìm kiếm ChromaDB bằng vector: {e}"
    else:
        # Fallback to Chroma's built-in embedding (MiniLM-L6-v2)
        try:
            results = collection.query(
                query_texts=[question],
                n_results=k
            )
        except Exception as e:
            return [], f"Lỗi tìm kiếm ChromaDB bằng text: {e}"
        
    if not results or not results['ids'] or not results['ids'][0]:
        return [], "Không tìm thấy thông tin phù hợp."
        
    chunk_ids = results['ids'][0]
    
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    
    contexts = []
    for cid in chunk_ids:
        if db_type == "postgres":
            cur.execute("SELECT text FROM chunks WHERE chunk_id = %s", (cid,))
        else:
            cur.execute("SELECT text FROM chunks WHERE chunk_id = ?", (cid,))
        row = cur.fetchone()
        if row:
            contexts.append(row[0])
            
    cur.close()
    conn.close()
    
    if not contexts:
        return [], "Tìm thấy chunk_id nhưng không lấy được text từ Database."
        
    if not gemini_client:
        return contexts, "Chế độ Retrieval-only do thiếu API Key."
        
    context_text = "\n\n---\n\n".join(contexts)
    prompt = f"Dựa vào thông tin sau:\n{context_text}\n\nHãy trả lời câu hỏi: {question}"
    try:
        response = gemini_client.models.generate_content(
            model='gemini-flash-lite-latest',
            contents=prompt
        )
        return contexts, response.text
    except Exception as e:
        return contexts, f"Lỗi gọi Gemini sinh câu trả lời: {e}"

def status():
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM chunks")
        db_count = cur.fetchone()[0]
    except Exception:
        db_count = 0
    cur.close()
    conn.close()
    
    collection = get_chroma_collection()
    try:
        chroma_count = collection.count() if collection else 0
    except Exception:
        chroma_count = 0
        
    return {
        "db_type": db_type,
        "db_documents_count": db_count,
        "chroma_chunks_count": chroma_count
    }
