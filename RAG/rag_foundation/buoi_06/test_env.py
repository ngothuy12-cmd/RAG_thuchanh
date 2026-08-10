import sys
import os

print(f"**Python interpreter đang sử dụng:** `{sys.executable}`")
print("-" * 30)
print("**Danh sách package đã cài & Kết quả import:**\n")

packages = {
    "streamlit": "streamlit",
    "google-genai": "google", 
    "chromadb": "chromadb",
    "psycopg": "psycopg",
    "python-dotenv": "dotenv"
}

for pkg, mod in packages.items():
    try:
        __import__(mod)
        print(f"- {pkg}: ✅ PASS")
    except ImportError as e:
        print(f"- {pkg}: ❌ FAIL ({e})")

print("-" * 30)
# ChromaDB status
try:
    import chromadb
    client = chromadb.HttpClient(host='localhost', port=8000)
    client.heartbeat()
    print("**Trạng thái ChromaDB:** Server (đang chạy trên localhost:8000)")
except Exception:
    print("**Trạng thái ChromaDB:** Embedded Local (sẽ lưu tại storage/chroma/)")

print("-" * 30)
# PostgreSQL status
try:
    import psycopg
    from dotenv import load_dotenv
    load_dotenv()
    
    password = os.getenv("POSTGRES_PASSWORD", "")
    try:
        # Check if postgres is running by connecting to default db
        conn = psycopg.connect(f"host=localhost port=5432 dbname=postgres user=postgres password={password}")
        print("**Trạng thái PostgreSQL:** ✅ Đang chạy")
        
        # Check if rag_db exists
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname='rag_db'")
        exists = cur.fetchone()
        
        if exists:
            print("**Trạng thái database rag_db:** ✅ Đã tồn tại")
        else:
            print("**Trạng thái database rag_db:** Chưa tồn tại, đang tiến hành tạo...")
            cur.execute("CREATE DATABASE rag_db")
            print("**Trạng thái database rag_db:** ✅ Đã tạo thành công")
        
        cur.close()
        conn.close()
        
    except psycopg.OperationalError as e:
        print(f"**Trạng thái PostgreSQL:** ❌ Không thể kết nối. (Bạn đã cài PostgreSQL và điền đúng mật khẩu vào .env chưa?)\nChi tiết lỗi: {e}")
        print("**Trạng thái database rag_db:** ⏳ Chưa thể kiểm tra do lỗi kết nối PostgreSQL.")
        
except ImportError:
    print("**Trạng thái PostgreSQL:** ⏳ Chưa thể kiểm tra do cài đặt package psycopg thất bại.")
