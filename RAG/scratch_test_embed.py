import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv('rag_advanced/buoi_08/.env')
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
contents = ["Text 1", "Text 2"]
response = client.models.embed_content(
    model='gemini-embedding-2',
    contents=contents,
    config=types.EmbedContentConfig(output_dimensionality=768)
)
print(len(response.embeddings))
