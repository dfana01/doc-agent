from langchain_core.tools import tool


SCORE_THRESHOLD = 0.7


@tool
def search(query: str, top_k: int = 5, document_id: str | None = None) -> dict:
    """Search indexed documents for information. Use this first to find content from uploaded documents. If results have low_confidence=true or no documents found, follow up with web_search."""
    from search import search
    
    results = search(query, top_k=top_k, document_id=document_id)
    low_confidence = not results or results[0].get("score", 1.0) < SCORE_THRESHOLD
    
    data = {
        "query": query,
        "documents": results or [],
        "document_count": len(results) if results else 0,
        "low_confidence": low_confidence,
    }
    
    if document_id:
        data["document_id"] = document_id
    
    if not results:
        data["message"] = "No documents found. Use web_search to find information online."
    elif low_confidence:
        data["message"] = f"Found {len(results)} documents but confidence is low. Consider using web_search."
    else:
        data["message"] = f"Found {len(results)} relevant documents."
    
    return data


@tool
def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web for current information. Use this after 'search' returns low_confidence=true or no documents, for real-time data, news, or topics not in uploaded documents."""
    from ddgs import DDGS
    
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    
    return {
        "results": [
            {"title": r["title"], "url": r["href"], "snippet": r["body"]}
            for r in results
        ]
    }


@tool
def document_processing(s3_path: str) -> dict:
    """Process and index a document from S3. Use when a user uploads a file. Extracts text (OCR for scans, vision for images), generates embeddings, and indexes for search."""
    from document import process_document
    
    result = process_document(s3_path)
    steps_summary = [
        {"step": s.name, "status": s.status, "message": s.message}
        for s in result.steps
    ]
    
    if result.success:
        return {
            "document_id": result.document_id,
            "document_name": result.filename,
            "s3_path": result.s3_path,
            "steps": steps_summary,
            "message": f"Document '{result.filename}' processed successfully. ID: {result.document_id}"
        }
    else:
        raise Exception(result.error)


@tool
def calculator(expression: str) -> dict:
    """Perform mathematical calculations. Use for arithmetic, sums, averages, percentages, and numerical analysis of data. Supports sum(), min(), max(), avg(), abs(), round()."""
    from simpleeval import EvalWithCompoundTypes
    
    functions = {
        "sum": sum,
        "min": min,
        "max": max,
        "avg": lambda x: sum(x) / len(x) if x else 0,
        "abs": abs,
        "round": round,
    }
    
    evaluator = EvalWithCompoundTypes(functions=functions)
    result = evaluator.eval(expression)
    return {"result": result, "expression": expression}


AGENT_TOOLS = [search, web_search, document_processing, calculator]


def system_health() -> dict:
    from health import run_all_health_checks, format_health_report
    
    health = run_all_health_checks()
    report = format_health_report(health)
    
    return {
        "report": report,
        "health": health.to_dict(),
    }


INTERNAL_TOOLS = {
    "system_health": system_health,
}


def execute_internal_tool(tool_name: str, **kwargs) -> dict:
    if tool_name not in INTERNAL_TOOLS:
        raise ValueError(f"Unknown internal tool: {tool_name}")
    return INTERNAL_TOOLS[tool_name](**kwargs)
