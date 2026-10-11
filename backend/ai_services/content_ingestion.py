"""Content ingestion service - handles PDF, DOCX, TXT, URL, Markdown, paste."""
import os
import re
import io
from urllib.parse import urlparse


def extract_text_from_pdf(file_bytes):
    import pdfplumber
    text = ""
    pages = 0
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
    return text, pages


def extract_text_from_docx(file_bytes):
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    return text, 1


def extract_text_from_txt(file_bytes):
    return file_bytes.decode("utf-8", errors="replace"), 1


def extract_text_from_markdown(file_bytes):
    return file_bytes.decode("utf-8", errors="replace"), 1


def extract_text_from_html(html_content):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    for script in soup(["script", "style"]):
        script.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return text


async def extract_from_url(url):
    import httpx
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or host in {"localhost", "127.0.0.1", "0.0.0.0"}:
        raise ValueError("URL must be a public http(s) URL")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "TransformIQ/1.0"})
        response.raise_for_status()
        max_bytes = 10 * 1024 * 1024
        if len(response.content) > max_bytes:
            raise ValueError("URL response is larger than the 10MB limit")
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            return extract_text_from_html(response.text), 1
        if not (content_type.startswith("text/") or "json" in content_type):
            raise ValueError(f"Unsupported URL content type: {content_type or 'unknown'}")
        return response.text, 1


def process_uploaded_file(filename, file_bytes):
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes), ext
    elif ext == ".docx":
        return extract_text_from_docx(file_bytes), ext
    elif ext in [".txt", ".text"]:
        return extract_text_from_txt(file_bytes), ext
    elif ext in [".md", ".markdown"]:
        return extract_text_from_markdown(file_bytes), ext
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def count_words(text):
    return len(text.split())


def estimate_reading_time(text):
    words = count_words(text)
    minutes = max(1, round(words / 200))
    return f"{minutes} minutes"
