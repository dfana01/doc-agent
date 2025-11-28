import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from s3 import download, upload_url, view_url
from extract import detect_type, extract_content
from search import index_chunks, search, generate_embeddings


@dataclass
class Step:
    name: str
    status: str
    message: str
    data: dict = field(default_factory=dict)


@dataclass 
class Result:
    document_id: str
    s3_path: str
    filename: str = ""
    success: bool = True
    error: str | None = None
    steps: list[Step] = field(default_factory=list)


def chunk_text(text: str, size: int = 1000, overlap: int = 200) -> list[str]:
    if not text:
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end]
        
        if end < len(text):
            for sep in ["\n\n", ". ", "! ", "? "]:
                pos = chunk.rfind(sep)
                if pos > size // 2:
                    chunk = chunk[:pos + len(sep)]
                    end = start + pos + len(sep)
                    break
        
        if chunk.strip():
            chunks.append(chunk.strip())
        
        if end >= len(text):
            break
        
        new_start = end - overlap
        if new_start <= start:
            new_start = start + 1
        start = new_start
    
    return chunks


def process_document(s3_path: str) -> Result:
    doc_id = str(uuid.uuid4())
    result = Result(document_id=doc_id, s3_path=s3_path)
    
    pipeline = [
        ("download", lambda: _download_step(s3_path)),
        ("detect", lambda ctx: _detect_step(ctx["key"], ctx["content"])),
        ("extract", lambda ctx: _extract_step(ctx["content"], ctx["doc_type"], ctx["mime"], ctx["ext"])),
        ("chunk", lambda ctx: _chunk_step(ctx["text"])),
        ("embed", lambda ctx: _embed_step(ctx["chunks"])),
        ("index", lambda ctx: _index_step(doc_id, s3_path, ctx)),
    ]
    
    ctx = {}
    for step_name, step_fn in pipeline:
        try:
            if step_name == "download":
                step_result = step_fn()
            else:
                step_result = step_fn(ctx)
            ctx.update(step_result["ctx"])
            result.steps.append(Step(step_name, "success", step_result["message"]))
            if step_name == "download":
                result.filename = ctx.get("filename", "")
        except Exception as e:
            result.steps.append(Step(step_name, "error", str(e)))
            result.success, result.error = False, str(e)
            return result
    
    return result


def _download_step(s3_path: str) -> dict:
    content, bucket, key = download(s3_path)
    filename = os.path.basename(key)
    ext = os.path.splitext(filename)[1].lower()
    return {
        "ctx": {"content": content, "key": key, "filename": filename, "ext": ext},
        "message": f"Downloaded {filename} ({len(content)} bytes)"
    }


def _detect_step(key: str, content: bytes) -> dict:
    doc_type, mime = detect_type(key, content)
    return {"ctx": {"doc_type": doc_type, "mime": mime}, "message": f"Type: {doc_type} ({mime})"}


def _extract_step(content: bytes, doc_type: str, mime: str, ext: str) -> dict:
    text, method = extract_content(content, doc_type, mime, ext)
    if not text.strip():
        raise ValueError("No content extracted")
    return {"ctx": {"text": text, "method": method}, "message": f"Extracted {len(text)} chars via {method}"}


def _chunk_step(text: str) -> dict:
    chunks = chunk_text(text)
    return {"ctx": {"chunks": chunks}, "message": f"Split into {len(chunks)} chunks"}


def _embed_step(chunks: list[str]) -> dict:
    embeddings = generate_embeddings(chunks)
    return {"ctx": {"embeddings": embeddings}, "message": f"Generated {len(embeddings)} embeddings"}


def _index_step(doc_id: str, s3_path: str, ctx: dict) -> dict:
    metadata = {
        "filename": ctx["filename"],
        "document_type": ctx["doc_type"],
        "processed_at": datetime.utcnow().isoformat()
    }
    count = index_chunks(doc_id, s3_path, ctx["chunks"], ctx["embeddings"], metadata)
    return {"ctx": {}, "message": f"Indexed {count} chunks"}
