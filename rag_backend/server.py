#!/usr/bin/env python3
"""Local RAG backend for EchoDocs.

    python rag_backend/server.py

Exposes /ingest (a PDF/text file, a URL, or pasted text) and /retrieve, which
the retrieve_context client-side tool in deployment/browser/app.js calls
directly from the browser. Runs on localhost only; never expose this port
publicly, since it has no auth of its own.
"""
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from flask import Flask, jsonify, request  # noqa: E402

from extract import extract_pdf, extract_url  # noqa: E402
from store import store  # noqa: E402

app = Flask(__name__)


@app.after_request
def add_cors(resp):
    # Dev-only, localhost-to-localhost: the browser page (port 3000) fetches
    # this backend (port 8001) directly, so it needs a permissive origin.
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.route("/ingest", methods=["POST", "OPTIONS"])
def ingest():
    if request.method == "OPTIONS":
        return "", 204
    try:
        if "file" in request.files:
            f = request.files["file"]
            data = f.read()
            if f.filename.lower().endswith(".pdf"):
                text = extract_pdf(data)
            else:
                text = data.decode("utf-8", errors="ignore")
            source = f.filename
        else:
            payload = request.get_json(force=True, silent=True) or {}
            url = (payload.get("url") or "").strip()
            text_in = (payload.get("text") or "").strip()
            if url:
                text = extract_url(url)
                source = url
            elif text_in:
                text = text_in
                source = "pasted text"
            else:
                return jsonify({"error": "provide a file, url, or text"}), 400

        count = store.ingest(text, source)
        return jsonify({"status": "ok", "source": source, "chunks": count})
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


@app.route("/retrieve", methods=["POST", "OPTIONS"])
def retrieve():
    if request.method == "OPTIONS":
        return "", 204
    payload = request.get_json(force=True, silent=True) or {}
    query = (payload.get("query") or "").strip()
    k = int(payload.get("k", 4))
    if not query:
        return jsonify({"error": "query is required"}), 400
    results = store.search(query, k=k)
    return jsonify({"chunks": results, "source": store.source})


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "loaded": store.source is not None,
        "source": store.source,
        "chunks": len(store.chunks),
    })


if __name__ == "__main__":
    print("RAG backend: http://localhost:8001")
    app.run(host="127.0.0.1", port=8001)
