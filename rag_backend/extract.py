"""Turn an upload or a URL into plain text."""
from __future__ import annotations

import io
import ssl
import urllib.request

import certifi
from bs4 import BeautifulSoup
from pypdf import PdfReader

# The framework Python this venv was built from has no system CA bundle of
# its own (a known macOS python.org gotcha), so urlopen's default SSL
# context can't verify any certificate. Point it at certifi's bundle
# explicitly instead of depending on Install Certificates.command having
# been run for this particular Python installation.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "EchoDocs/1.0"})
    with urllib.request.urlopen(req, timeout=20, context=_SSL_CONTEXT) as res:
        html = res.read()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n")
