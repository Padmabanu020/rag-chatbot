"""Local persistent ChromaDB vector store (cosine similarity)."""
import chromadb
from django.conf import settings

_client = None


def collection():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
    return _client.get_or_create_collection("documents", metadata={"hnsw:space": "cosine"})


def add_chunks(doc_id, doc_name, chunks, embeddings):
    collection().add(
        ids=[f"{doc_id}-{c['index']}" for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embeddings,
        metadatas=[{"doc_id": doc_id, "document": doc_name, "page": c["page"] or 0, "chunk_index": c["index"]} for c in chunks],
    )


def delete_document(doc_id):
    collection().delete(where={"doc_id": doc_id})


def search(embedding, k):
    col = collection()
    if col.count() == 0:
        return []
    res = col.query(query_embeddings=[embedding], n_results=min(k, col.count()),
                    include=["documents", "metadatas", "distances"])
    return [
        {"text": t, "meta": m, "score": round(1 - d, 4)}
        for t, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]
