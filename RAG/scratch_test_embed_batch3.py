import os
from google import genai
from dotenv import load_dotenv

load_dotenv('rag_advanced/buoi_08/.env')
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
print([x for x in dir(client.models) if 'embed' in x])
