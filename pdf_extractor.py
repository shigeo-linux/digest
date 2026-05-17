import os

CHUNK_SIZE = 250_000  # characters per API call


def extract_text(filepath):
    """Extract all text from a PDF. Returns (text, page_count)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("pypdf not installed. Run: pip3 install --user pypdf")

    reader = PdfReader(filepath)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return '\n\n'.join(pages), len(reader.pages)


def split_chunks(text):
    """Split text into chunks that fit within API token limits."""
    return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
