import { useEffect, useRef, useState } from "react";
import { api } from "./api";

const SUGGESTIONS = [
  "How many days of annual leave do I get?",
  "Who approves expense claims above 5000 rupees?",
  "What is the dress code?",
];

function Pending() {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSecs((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="pending" role="status">
      <span className="dots">
        <i />
        <i />
        <i />
      </span>
      Thinking… {secs}s
    </div>
  );
}

function Turn({ turn }) {
  // Hide citation markers like [1] since sources are not shown
  const clean = (turn.answer || "").replace(/\s*\[\d+\]/g, "");
  return (
    <>
      <div className="bubble user">{turn.question}</div>
      <div className="bubble bot">
        {turn.error ? (
          <p className="error">
            {turn.error}. Check that the backend is running, then ask again.
          </p>
        ) : turn.answer == null ? (
          <Pending />
        ) : (
          <p className="answer">{clean}</p>
        )}
      </div>
    </>
  );
}

export default function App() {
  const [docs, setDocs] = useState([]);
  const [turns, setTurns] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState("");
  const endRef = useRef(null);

  const readyCount = docs.filter((d) => d.status === "ready").length;

  const loadDocs = () =>
    api
      .documents()
      .then((d) => setDocs(d.documents))
      .catch((e) => setNotice(e.message));

  useEffect(() => {
    (async () => {
      try {
        await loadDocs();
        const history = await api.history();
        setTurns(history.messages || []);
      } catch (error) {
        console.error("Initialization error:", error);
        setNotice(error.message || "Failed to initialize application");
      }
    })();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  async function ask(raw) {
    const question = raw.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);
    setTurns((t) => [...t, { question, answer: null, sources: [] }]);
    const patch = (p) =>
      setTurns((t) =>
        t.map((x, i) => (i === t.length - 1 ? { ...x, ...p } : x)),
      );
    try {
      const r = await api.chat(question);
      patch({ answer: r.answer, sources: r.sources || [] });
    } catch (err) {
      patch({ error: err.message });
    } finally {
      setBusy(false);
    }
  }

  const send = (e) => {
    e.preventDefault();
    ask(input);
  };
  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ask(input);
    }
  };

  async function uploadFiles(files) {
    if (!files.length) return;
    setUploading(true);
    setNotice("");
    for (const f of files) {
      try {
        await api.upload(f);
      } catch (err) {
        setNotice(`${f.name}: ${err.message}`);
      }
    }
    await loadDocs();
    setUploading(false);
  }
  const onPick = (e) => {
    const files = [...e.target.files];
    e.target.value = "";
    uploadFiles(files);
  };
  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (!uploading) uploadFiles([...e.dataTransfer.files]);
  };

  async function remove(id) {
    await api.remove(id).catch((e) => setNotice(e.message));
    loadDocs();
  }

  return (
    <div className="app">
      <aside className="library">
        <header>
          <h1>Document Q&amp;A</h1>
          <p className="muted">
            Runs fully on this machine. Answers come only from your uploaded
            documents.
          </p>
        </header>

        <label
          className={
            "upload" + (uploading ? " busy" : "") + (dragging ? " over" : "")
          }
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <strong>{uploading ? "Processing…" : "Add documents"}</strong>
          <span>
            {uploading
              ? "Splitting into chunks and indexing"
              : "Drop PDF, DOCX, TXT or MD files here, or click to browse"}
          </span>
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md"
            onChange={onPick}
            disabled={uploading}
            hidden
          />
        </label>

        {notice && (
          <p className="error notice" role="alert">
            {notice}
          </p>
        )}

        <ul className="docs" aria-label="Documents">
          {docs.length === 0 && (
            <li className="none muted">
              No documents yet. Add one to get started.
            </li>
          )}
          {docs.map((d) => (
            <li key={d.id}>
              <div className="doc-main">
                <strong title={d.name}>{d.name}</strong>
                <span
                  className={
                    "pill " +
                    (d.status === "ready"
                      ? "ok"
                      : d.status === "failed"
                        ? "bad"
                        : "wait")
                  }
                >
                  {d.status === "ready"
                    ? `${d.chunks} chunks`
                    : d.status === "failed"
                      ? "Failed to index"
                      : "Processing"}
                </span>
              </div>
              <button
                onClick={() => remove(d.id)}
                aria-label={`Delete ${d.name}`}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="chat">
        <div className="thread">
          {turns.length === 0 && (
            <div className="empty">
              <h2>Ask about your documents</h2>
              {readyCount === 0 ? (
                <p className="muted">
                  Add a document on the left, then ask a question.
                </p>
              ) : (
                <>
                  <p className="muted">Try one of these, or type your own.</p>
                  <div className="suggest">
                    {SUGGESTIONS.map((s) => (
                      <button key={s} onClick={() => ask(s)} disabled={busy}>
                        {s}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
          {turns.map((t, i) => (
            <Turn key={i} turn={t} />
          ))}
          <div ref={endRef} />
        </div>

        <form className="composer" onSubmit={send}>
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            placeholder={
              readyCount
                ? "Ask a question about your documents"
                : "Add a document first"
            }
            disabled={readyCount === 0}
            aria-label="Question"
          />
          <button disabled={busy || !input.trim() || readyCount === 0}>
            {busy ? "Thinking…" : "Ask"}
          </button>
        </form>
      </main>
    </div>
  );
}
