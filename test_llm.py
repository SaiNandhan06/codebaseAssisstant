import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client =  genai.Client()

response = client.models.generate_content(
    model = "gemini-3.5-flash",
    contents = "In one sentence, explain what RAG (retrieval-augmented generation) is."
)

print(response.text)