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
    print(f"Error list of strings: {e}")

try:
    response = client.models.embed_content(
        model='gemini-embedding-2',
        contents=[
            types.EmbedContentRequest(content="Text 1"), 
            types.EmbedContentRequest(content="Text 2")
        ],
        config=types.EmbedContentConfig(output_dimensionality=768)
    )
    print(f"List of requests -> len(embeddings) = {len(response.embeddings)}")
except Exception as e:
    print(f"Error list of requests: {e}")
