import io
import os
import mimetypes

from config import get_config


def detect_type(filepath: str, content: bytes) -> tuple[str, str]:
    mime, _ = mimetypes.guess_type(filepath)
    mime = mime or "application/octet-stream"
    ext = os.path.splitext(filepath)[1].lower()
    
    if mime.startswith("image/") or ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        return "image", mime
    
    if ext == ".pdf" or mime == "application/pdf":
        return ("text_pdf" if _pdf_has_text(content) else "scanned_pdf"), mime
    
    if ext in [".txt", ".md", ".rst", ".csv", ".json", ".doc", ".docx"]:
        return "text", mime
    
    return "unknown", mime


def _pdf_has_text(content: bytes) -> bool:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content))
        for page in reader.pages[:3]:
            text = page.extract_text() or ""
            if len(text.strip()) > 50:
                return True
    except Exception:
        pass
    return False


def extract_content(content: bytes, doc_type: str, mime: str, ext: str) -> tuple[str, str]:
    extractors = {
        "text_pdf": lambda: (_extract_pdf(content), "pdf"),
        "scanned_pdf": lambda: (_extract_ocr(content, mime), "ocr"),
        "image": lambda: _extract_image(content, mime),
        "text": lambda: (_extract_text(content, ext), "text"),
    }
    
    extractor = extractors.get(doc_type)
    if extractor:
        return extractor()
    return content.decode("utf-8", errors="replace"), "raw"


def _extract_pdf(content: bytes) -> str:
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(content))
    pages = [p.extract_text() for p in reader.pages if p.extract_text()]
    return "\n\n".join(pages)


def _extract_text(content: bytes, ext: str) -> str:
    if ext in [".doc", ".docx"]:
        import docx
        doc = docx.Document(io.BytesIO(content))
        return "\n\n".join(p.text for p in doc.paragraphs)
    return content.decode("utf-8", errors="replace")


def _extract_image(content: bytes, mime: str) -> tuple[str, str]:
    text = _extract_ocr(content, mime)
    if len(text.strip()) > 50:
        return text, "ocr"
    return _extract_vision(content, mime), "vision"


def _extract_ocr(content: bytes, mime: str) -> str:
    config = get_config()
    
    if config.is_local:
        import pytesseract
        from PIL import Image
        
        if mime == "application/pdf":
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(content)
            return "\n\n".join(pytesseract.image_to_string(img) for img in images)
        
        return pytesseract.image_to_string(Image.open(io.BytesIO(content)))
    
    import boto3
    textract = boto3.client("textract", region_name=config.aws_region)
    resp = textract.detect_document_text(Document={"Bytes": content})
    lines = [b["Text"] for b in resp.get("Blocks", []) if b["BlockType"] == "LINE"]
    return "\n".join(lines)


def _extract_vision(content: bytes, mime: str) -> str:
    import base64
    from llm import get_openai_client
    
    b64 = base64.b64encode(content).decode()
    client = get_openai_client()
    
    resp = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in detail. Include any visible text, objects, and relevant information."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
            ]
        }]
    )
    return resp.choices[0].message.content

