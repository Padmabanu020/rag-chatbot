"""Semantic retrieval + grounded answer generation with citations."""
from django.conf import settings
from . import ollama_client, vectorstore

NOT_FOUND = "I couldn't find that in the uploaded documents."

SYSTEM_PROMPT = (
    "You are a document Q&A assistant. Answer ONLY from the numbered context excerpts provided. "
    "Cite the supporting excerpt number in square brackets after every claim, e.g. [1] or [2][3]. "
    f'If the excerpts do not contain the answer, reply exactly: "{NOT_FOUND}" '
    "Never use outside knowledge and never invent citations."
)


def answer(question, top_k=None):
    top_k = top_k or settings.TOP_K
    query_vec = ollama_client.embed([question])[0]
    hits = [h for h in vectorstore.search(query_vec, top_k) if h["score"] >= settings.MIN_SCORE]
    if not hits:
        return {"answer": NOT_FOUND, "sources": []}

    sources = [
        {
            "id": i,
            "doc_id": h["meta"]["doc_id"],
            "document": h["meta"]["document"],
            "page": h["meta"]["page"] or None,
            "chunk_index": h["meta"]["chunk_index"],
            "score": h["score"],
            "text": h["text"],
        }
        for i, h in enumerate(hits, 1)
    ]
    context = "\n\n".join(
        f"[{s['id']}] ({s['document']}{', page ' + str(s['page']) if s['page'] else ''})\n{s['text']}" for s in sources
    )
    reply = ollama_client.chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
    ])
    return {"answer": reply, "sources": sources}
