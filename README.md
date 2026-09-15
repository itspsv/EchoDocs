# EchoDocs

EchoDocs is a voice-first RAG (retrieval-augmented generation) assistant. Upload a document — a PDF, a plain text file, or a URL — then ask questions about it out loud. The agent retrieves the passages relevant to your question and answers with spoken audio, grounded only in what the document actually says rather than the model's own general knowledge.

Built for the AssemblyAI Voice Agent Hackathon.

## How it works

1. You load a document through the browser page — upload a PDF or text file, or paste a URL.
2. A local backend extracts the text, splits it into overlapping chunks, embeds each chunk, and stores the vectors in a FAISS index.
3. You start a voice call with the agent over AssemblyAI's Voice Agent API.
4. When you ask a question, the agent calls a `retrieve_context` tool with a short search query. That tool is answered by the browser page itself rather than by AssemblyAI's servers: it queries the local backend, gets back the most relevant passages, and returns them to the agent.
5. The agent answers using only those passages, speaking the answer back to you. If nothing relevant is found, it says so instead of guessing.

## Tech stack

- **AssemblyAI Voice Agent API** — real-time speech-to-text, turn detection, text-to-speech, and tool calling over a WebSocket session.
- **Python (standard library)** — `deployment/browser/server.py` serves the page, mints short-lived session tokens, and keeps the AssemblyAI API key server-side, never exposed to the browser.
- **Flask** — the local RAG backend (`rag_backend/`).
- **FAISS** — vector similarity search over a document's chunk embeddings.
- **sentence-transformers** (`all-MiniLM-L6-v2`) — local embedding model; no external embedding API or key required.
- **pypdf** / **BeautifulSoup** — text extraction from PDFs and web pages.
- **Vanilla HTML/CSS/JS** — the browser page (`deployment/browser/`), including the audio capture/playback pipeline and the client-side tool-call handling.

## Project structure

```
EchoDocs/
├── agents/
│   └── rag.jsonc            # the EchoDocs agent: system prompt, voice, and the retrieve_context tool
├── deployment/
│   └── browser/
│       ├── index.html       # the page: document upload panel, transcript, call controls
│       ├── app.js            # websocket session, audio pipeline, tool-call handling
│       ├── server.py         # serves the page, mints tokens, keeps the API key server-side
│       └── echo-icon.png
├── rag_backend/
│   ├── server.py             # Flask API: /ingest, /retrieve, /status
│   ├── store.py               # chunking, embedding, FAISS index, relevance threshold
│   ├── extract.py             # PDF and URL text extraction
│   └── requirements.txt
├── lib.py                    # shared helpers: env loading, JSONC parsing, AssemblyAI API calls
├── publish.py                 # publishes agents/rag.jsonc to your AssemblyAI account
└── requirements.txt
```

Two separate Python environments are involved: the top-level project (`lib.py`, `publish.py`, `deployment/browser/`) uses only the standard library, while `rag_backend/` has its own virtual environment for FAISS, sentence-transformers, and their dependencies.

## Use cases

- Studying from a textbook chapter, lecture cheat sheet, or course PDF by asking questions instead of re-reading.
- Getting quick spoken answers out of long reference material — technical docs, onboarding guides, a handbook — without needing to be at a screen.
- Querying a web article or blog post hands-free, by pasting its URL instead of downloading a file.

## Notes

- One document is active at a time — loading a new one replaces the previous index entirely.
- A retrieval below a relevance threshold is dropped rather than handed to the model, so an off-topic question gets an honest "the document doesn't cover that" instead of an answer built on the nearest-but-irrelevant passage.
- PDF text extraction requires selectable text; scanned/image-only PDFs aren't OCR'd.
- Because `retrieve_context` is answered by the browser rather than by AssemblyAI's servers, this agent works in the browser deployment only, not over a phone call.
