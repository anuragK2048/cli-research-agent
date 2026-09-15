from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def embed(text: str|list):
    return model.encode(text, convert_to_tensor=True)

def similarity_ranking(doc_embeddings, query_embedding):
    results = util.semantic_search(
        query_embedding,
        doc_embeddings,
        # top_k=10
        top_k=len(doc_embeddings)
    )[0]
    return results