import os
import numpy as np
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()

def get_embedding(text):
    result = client.models.embed_content(
        model = "gemini-embedding-001",
        contents = text
    )

    return np.array(result.embeddings[0].values)

def cosine_similarity(vec_a,vec_b):
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)

    return dot_product / (norm_a * norm_b)

sentence_1 = "The cat sat on the mat."
sentence_2 = "A feline rested on the rug."
sentence_3 = "The stock market crashed yesterday."

emb_1 = get_embedding(sentence_1)
emb_2 = get_embedding(sentence_2)
emd_3 = get_embedding(sentence_3)

print(f"Embeddding shape: {emb_1.shape}")
print(f"Similarity (cat/mat vs feline/rug) : {cosine_similarity(emb_1, emb_2):.4f}")
print(f"Similarity (cat/mat vs stock market) : {cosine_similarity(emb_1, emd_3):.4f}")