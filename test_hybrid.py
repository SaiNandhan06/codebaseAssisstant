import re
from dotenv import load_dotenv
from google import genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from rank_bm25 import BM25Okapi

load_dotenv()
client = genai.Client()
db = QdrantClient(host="localhost",port=6333)

def get_embeddings(text):
    result = client.models.embed_content(model="gemini-embedding-001", contents =text)
    return result.embeddings[0].values

def  tokenize(text):
    return re.findall(r"\w+",text.lower())

documents = [
    "def calculate_total(items): return sum(item.price for item in items)",
    "class UserAuth: handles login, logout and session tokens",
    "The cat sat on the mat.",
    "def calculate_average(numbers): return sum(numbers)/ len(numbers)",
]

tokenized_docs = [tokenize(doc) for doc in documents]
bm25 = BM25Okapi(tokenized_docs)

sample_vector = get_embeddings(documents[0])
if db.collection_exists("hybrid_test"):
    db.delete_collection("hybrid_test")
db.create_collection(
    collection_name="hybrid_test",
    vectors_config = VectorParams(size=len(sample_vector), distance=Distance.COSINE)
)
points = [
    PointStruct(id=i, vector=get_embeddings(doc), payload={"text": doc})
    for i,doc in enumerate(documents)
]
db.upsert(collection_name="hybrid_test", points=points)

def hybrid_search(query, k =60):
    bm25_scores = bm25.get_scores(tokenize(query))
    bm25_ranked = sorted(range(len(documents)), key = lambda i: bm25_scores[i],reverse=True)
    bm25_rank_of = {doc_id:rank for rank,doc_id in enumerate(bm25_ranked)}

    query_vector = get_embeddings(query)
    dense_results = db.query_points(
        collection_name="hybrid_test",
        query=query_vector,
        limit = len(documents)
    ).points
    dense_rank_of = {r.id: rank for rank, r in enumerate(dense_results)}

    rrf_scores = {}
    for doc_id in range(len(documents)):
        score=0
        if doc_id in bm25_rank_of:
            score += 1/ (k + bm25_rank_of[doc_id])
        if doc_id in dense_rank_of:
            score += 1 / (k + dense_rank_of[doc_id])
        rrf_scores[doc_id] = score

    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    for doc_id, score in ranked:
        print(f"RRF Score: {score:.4f} | Text: {documents[doc_id]}")


print("Hybrid Search: 'calculate_total' (exact term): ")
hybrid_search("calculate_total")

print("\nHybrid Search: 'sum up prices for a list of items' (paraphrased): ")
hybrid_search("sum up prices for a list of items")