import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv('rag_advanced/buoi_08/.env')
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
try:
    response = client.models.embed_content(
        model='gemini-embedding-2',
        contents=["Text 1", "Text 2"],
        config=types.EmbedContentConfig(output_dimensionality=768)
    )
    print(f"List of strings -> len(embeddings) = {len(response.embeddings)}")
except Exception as e:
    print(f"Error: {e}")

try:
    response = client.models.embed_content(
        model='gemini-embedding-2',
        contents=[{"text": "Text 1"}, {"text": "Text 2"}],
    )
    print(f"List of dicts -> len(embeddings) = {len(response.embeddings)}")
except Exception as e:
    print(f"Error list of dicts: {e}")
