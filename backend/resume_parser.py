"""
Extracts raw text from uploaded resume files (PDF or plain text).
Structured extraction (skills/experience/education) is handled separately
by llm_service.py since that requires semantic understanding, not just parsing.
"""
import io
import pdfplumber


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text content from a PDF file's bytes."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def extract_text_from_upload(filename: str, file_bytes: bytes) -> str:
    """
    Dispatch based on file extension. Supports .pdf and .txt.
    Raises ValueError for unsupported types.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
    elif lower.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: {filename}. Use .pdf or .txt")

    if not text or len(text.strip()) < 20:
        raise ValueError("Could not extract meaningful text from this file. It may be a scanned/image-based PDF.")

    return text
