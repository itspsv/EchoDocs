# EchoDocs

EchoDocs is a voice RAG assistant.

Upload a document. Ask questions about it out loud. Get spoken answers grounded in that document, not in the model's general knowledge.

Built for the AssemblyAI Voice Agent Hackathon.

## How it works

1. Load a document. Upload a PDF or text file, or paste a URL.
2. The backend extracts the text, splits it into chunks, and embeds each one. The vectors go into a FAISS index.
3. Start a voice call with the agent over AssemblyAI's Voice Agent API.
4. Ask a question. The agent calls a `retrieve_context` tool. The browser page answers it, not AssemblyAI's servers. It queries the local backend and pulls back the most relevant passages.
5. The agent answers using only those passages. If nothing relevant turns up, it says so instead of guessing.

## Tech stack

- **AssemblyAI Voice Agent API.** Speech to text, turn detection, text to speech, and tool calling, all over one WebSocket session.
- **Python standard library.** `deployment/browser/server.py` serves the page and mints short-lived tokens. The API key never reaches the browser.
- **Flask.** Runs the local RAG backend.
- **FAISS.** Vector search over the document's chunks.
- **sentence-transformers** (`all-MiniLM-L6-v2`). Local embeddings. No external API or key needed.
- **pypdf and BeautifulSoup.** Pull text out of PDFs and web pages.
- **Plain HTML, CSS, and JS.** The browser page, the audio pipeline, and the tool call handling.

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

Two Python environments live here. The top-level project (`lib.py`, `publish.py`, `deployment/browser/`) uses only the standard library. `rag_backend/` has its own virtual environment for FAISS, sentence-transformers, and everything they need.

## Use cases

- Study from a textbook chapter or a course PDF. Ask questions instead of rereading.
- Get quick spoken answers from long reference docs. No need to sit at a screen.
- Ask about a web article hands free. Just paste the URL, no download needed.

## Notes

- One document at a time. Loading a new one replaces the old index.
- Low-relevance retrievals get dropped. An off-topic question gets an honest "the document doesn't cover that" instead of a made-up answer.
- PDF extraction needs selectable text. Scanned or image-only PDFs won't work.
- `retrieve_context` runs in the browser, not on AssemblyAI's servers. So this agent only works in the browser, not on a phone call.
