# Local Document Q&A Chatbot (RAG)

A Retrieval-Augmented Generation app that answers questions about your own documents **entirely on your machine**.
The LLM and embeddings run through [Ollama](https://ollama.com); vectors live in a local ChromaDB store; metadata and chat history live in Microsoft SQL Server. No cloud API is called.

| Layer | Technology |
|-------|-----------|
| LLM + embeddings | Ollama (`llama3.2`, `nomic-embed-text`) |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| Backend | Python, Django |
| Relational DB | Microsoft SQL Server (`mssql-django`) |
| Frontend | React (Vite) |

## How it works

```
Upload ─► load (PDF/DOCX/TXT/MD) ─► chunk (800 chars, 150 overlap) ─► embed (Ollama) ─► ChromaDB
Ask    ─► embed question ─► top-k similarity search ─► build numbered context ─► local LLM ─► answer + [n] citations + source chunks
```

* **Grounding:** the prompt restricts the model to the retrieved excerpts and requires `[n]` citations. Chunks below a similarity floor (`MIN_SCORE`) are discarded; if nothing relevant remains the bot says it could not find the answer instead of guessing.
* **Citations:** every response returns a `sources` array (document, page, chunk index, similarity score, chunk text). The UI turns `[n]` markers into clickable chips that open the matching chunk.
* **SQL Server** stores documents (name, status, chunk count) and chat history. **ChromaDB** stores the chunk vectors.

## Prerequisites

* Python 3.10+, Node.js 18+
* [Ollama](https://ollama.com/download)
* SQL Server (local install, or `docker compose up -d` using the included `docker-compose.yml`)
* Microsoft ODBC Driver 18 for SQL Server ([install guide](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server))

## Setup

### 1. Ollama models
```bash
ollama pull llama3.2
ollama pull nomic-embed-text
ollama serve            # skip if Ollama already runs as a service
```
Any chat model works; set `LLM_MODEL` in `.env` (for example `mistral` or `qwen2.5`).

### 2. Database
Start SQL Server and create an empty database:
```bash
docker compose up -d
docker compose exec mssql /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "Your_Strong_Passw0rd" -C -Q "CREATE DATABASE ragdb"
```
(With an existing SQL Server, just create a database named `ragdb`.)

### 3. Configuration
```bash
cp .env.example .env     # then edit DB_PASSWORD etc. to match your SQL Server
```

### 4. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```
Check `http://localhost:8000/api/health/` shows `"ollama": true`.

### 5. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**, add a document, and ask a question.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health/` | Ollama status and installed models |
| GET | `/api/documents/` | List indexed documents |
| POST | `/api/documents/` | Upload and index a file (`multipart`, field `file`; pdf, docx, txt, md) |
| DELETE | `/api/documents/<id>/` | Remove a document and its vectors |
| POST | `/api/chat/` | Ask a question |
| GET | `/api/history/` | Last 50 chat turns |

```bash
curl -X POST localhost:8000/api/chat/ -H "Content-Type: application/json" \
     -d '{"question": "What is the refund policy?"}'
```
```json
{
  "answer": "Refunds are issued within 14 days of purchase [1].",
  "sources": [
    {"id": 1, "document": "policy.pdf", "page": 3, "chunk_index": 12, "score": 0.81, "text": "..."}
  ]
}
```

## Configuration reference (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_MODEL` / `EMBED_MODEL` | `llama3.2` / `nomic-embed-text` | Ollama models |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `150` | Characters per chunk / overlap |
| `TOP_K` | `4` | Chunks retrieved per question |
| `MIN_SCORE` | `0.30` | Minimum cosine similarity to use a chunk |
| `DB_*` | see `.env.example` | SQL Server connection |

## Project structure

```
backend/
  config/            Django settings and URLs
  rag/
    models.py        Document, ChatMessage (SQL Server)
    views.py         REST endpoints
    services/
      ollama_client.py   embeddings + chat calls to local Ollama
      ingestion.py       load -> chunk -> embed -> store
      vectorstore.py     ChromaDB wrapper
      retrieval.py       search + grounded prompt + citations
frontend/src/        React app (App.jsx, api.js, styles.css)
```

## Notes and limitations

* Scanned/image-only PDFs have no text layer and need OCR first.
* Ingestion is synchronous, so large files block the upload request until indexing finishes. A task queue (Celery) is the natural next step.
* Small local models can occasionally cite imperfectly; the source panel lets you verify each answer.
* Re-uploading the same file creates a second copy; delete the old one first.

## Troubleshooting

* **`Can't open lib 'ODBC Driver 18...'`**: install the ODBC driver, or set `DB_DRIVER` to the installed name.
* **SSL/login errors**: confirm `DB_PASSWORD` matches the SQL Server SA password and the `ragdb` database exists.
* **`Ollama unavailable`**: run `ollama serve` and confirm both models appear in `ollama list`.
