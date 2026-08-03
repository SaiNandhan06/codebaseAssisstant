import re
from rank_bm25 import BM25Okapi

def tokenize(text):
    return re.findall(r"\w+",text.lower())

documents = [
    "def calculate_total(items): return sum(item.price for item in items)",
    "class UserAuth: handles login,logout and session tokens",
    "The cat sat on the mat.",
    "def calculate_average(numbers): return sum(numbers)/len(numbers)"
]

tokenized_docs = [tokenize(doc) for doc in documents]
bm25 = BM25Okapi(tokenized_docs)

def search(query):
    tokenized_query = tokenize(query)
    scores = bm25.get_scores(tokenized_query)
    ranked = sorted(zip(scores,documents) , key = lambda x : x[0],reverse = True)
    for score,doc in ranked:
        print(f"Score : {score:.4f} | Text : {doc}")

# print("Query:", query)
# print("Tokenized Query:", tokenized_query)
# print("First document tokens:", tokenized_docs[0])
# print("Second document tokens:", tokenized_docs[1])
# print("Scores:", scores)
print("Exact Match Query: ")
search('calculate_total')

print("\nParaphrased query: ")
search("sum up prices for a list of items")
