from sentence_transformers import CrossEncoder

model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")

query = "How do I total up prices for a list of items?"

candidates = [
    "def calculate_total(items): return sum(item.price for item in items)",
    "class UserAuth: handles login, logout and session tokens",
    "The cat sat on the mat.",
    "def calculate_average(numbers): return sum(numbers) / len(numbers)",
]

pairs = [(query,doc) for doc in candidates]

scores = model.predict(pairs)

ranked = sorted(zip(scores, candidates) , key=lambda x: x[0], reverse=True)

for score, doc in ranked:
    print(f"Score: {score:.4f} | Text: {doc}")

