import os
from dotenv import load_dotenv
from google import genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

load_dotenv()
client = genai.Client()
db = QdrantClient(host="localhost",port=6333)

def get_embeddings(text):
    result = client.models.embed_content(
        model = "gemini-embedding-001",
        contents =text
    )
    return result.embeddings[0].values

documents = [
    "def calculate-total(items) : return sum(item.price for item in items)",
    "class UserAuth: handles login, logout and session tokens",
    "The cat sat on the mat."
]

sample_vector = get_embeddings(documents[0])
db.recreate_collection(
    collection_name = "test_collection",
    vectors_config=VectorParams(size=len(sample_vector),distance=Distance.COSINE)
)

points=[]
for i, doc in enumerate(documents):
    vector = get_embeddings(doc)
    points.append(PointStruct(id=i,vector=vector,payload={"text":doc}))

db.upsert(collection_name = "test_collection",points=points)

query = "How do I total up prices for a list of items?"
query_vector = get_embeddings(query)

results = db.query_points(collection_name="test_collection", query=query_vector, limit=2)

for r in results.points:
    print(f"Score: {r.score:.4f} | Text: {r.payload['text']}")
    