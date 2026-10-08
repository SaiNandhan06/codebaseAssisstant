import re
from dotenv import load_dotenv
from google import genai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

load_dotenv()
gemini = genai.Client()
db = QdrantClient(host="localhost",port=6333)
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")

def get_embeddings(text):
    result = gemini.models.embed_content(
        model = "gemini-embedding-001",
        contents = text,
    )
    return result.embeddings[0].values

def tokenize(text):
    return re.findall(r"\w+",text.lower())

documents = [
    "def calculate_total(items): return sum(item.price for item in items)",
    "class UserAuth: handles login, logout and session tokens",
    "The cat sat on the mat.",
    "def calculate_average(numbers): return sum(numbers) / len(numbers)",
]

tokenised_docs = [tokenize(doc) for doc in documents]
bm25 = BM25Okapi(tokenised_docs)

sample_vector = get_embeddings(documents[0])
if db.collection_exists("full_pipeline_test"):
    db.delete_collection("full_pipeline_test")
db.create_collection(
    collection_name="full_pipeline_test",
    vectors_config = VectorParams(size=len(sample_vector),distance=Distance.COSINE)
)

points = [
    PointStruct(id = i, vector = get_embeddings(doc), payload = {"text": doc})
    for i, doc in enumerate(documents)
]
db.upsert(collection_name="full_pipeline_test", points=points)

def hybrid_search(query, k = 60,top_n=3):
    bm25_scores = bm25.get_scores(tokenize(query))
    bm25_ranked = sorted(range(len(documents)), key=lambda i : bm25_scores[i], reverse=True)
    bm25_rank_of = {doc_id : rank for rank, doc_id in enumerate(bm25_ranked)}

    query_vector = get_embeddings(query)
    dense_results =  db.query_points(collection_name="full_pipeline_test", query =query_vector, limit=len(documents)).points
    dense_rank_of = {r.id: rank for rank, r in enumerate(dense_results)}

    rrf_scores = {}
    for doc_id in range(len(documents)):
        score = 0
        if doc_id in bm25_rank_of:
            score += 1 / (k + bm25_rank_of[doc_id])
        if doc_id in dense_rank_of:
            score += 1 / (k + dense_rank_of[doc_id])
        rrf_scores[doc_id] = score

    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [documents[doc_id] for doc_id, _ in ranked[:top_n]]

def rerank(query, candidates , top_n=2):
    pairs = [(query,doc) for doc in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores,candidates) , key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked[:top_n]]

def answer_question(query):
    shortlist = hybrid_search(query, top_n=3)
    best_matches = rerank(query,shortlist,top_n = 2)

    context = "\n".join(best_matches)
    prompt = f"""Answer the question using ONLY the context below. Cite which line you used.

Context:
{context}

Question: {query}
"""
    response = gemini.models.generate_content(
        model = "gemini-3.5-flash",
        contents = prompt,
    )
    return response.text , best_matches


query = "How do I total up prices for a list of items?"
answer, sources = answer_question(query)   

print("SOURCES USED")
for s in sources:
    print(f"- {s}")

print("\n ANSWER")
print(answer)