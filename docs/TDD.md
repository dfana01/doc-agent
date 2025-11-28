# AI Agent Technical Design

LangGraph-based multi-tool agent for document processing.

## Overview

An AI agent that autonomously selects and chains tools to answer queries about documents.

**In Scope:** Document ingestion with logging, chat UI with tool visibility

**Out of Scope:** load testing (single-user tool)

## Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| **Backend** | FastAPI | Native Pydantic validation, auto-generated OpenAPI docs, async support. Same codebase for local dev and Lambda via Mangum. |
| **Compute** | Lambda + async polling | Async execution - Lambda self-invokes, returns immediately. DynamoDB stores job state for traceability. Simpler than SSE, avoids API Gateway timeout. |
| **Agent Pattern** | LangGraph prebuilt ReAct | `create_react_agent` delegates tool selection to agent. More agentic - minimal manual routing. |
| **LLM** | Claude Sonnet (Anthropic API) | Direct API for simplicity/velocity. No AWS Bedrock complexity. |
| **Vision** | GPT-4o (OpenAI API) | Describes images without text (photos, diagrams). Direct API. |
| **OCR** | AWS Textract | Extracts text from document images (PDFs, scans). AWS-native. |
| **Math Tool** | Expression parser (`simpleeval`) | Safe, fast, no sandbox needed. Covers sum, avg, min, max, basic arithmetic. |
| **Embeddings** | OpenAI `text-embedding-3-small` | Cost-effective, 1536 dimensions. Good quality/cost balance for semantic search. |
| **Vector DB** | OpenSearch | AWS-native, k-NN plugin, managed service. |
| **Web Search** | Pluggable (default: ddgs) | DuckDuckGo - no API key required. Abstracted interface for easy swap. |
| **Frontend** | Thin React client | Backend-driven decisions. Config-driven UI. Changes on backend don't require frontend changes. |
| **API Contracts** | Pydantic | Type-safe models + generates TypeScript schema. Single source of truth for API types. |
| **Tool Architecture** | `@tool` decorator + split | `AGENT_TOOLS` (LLM-callable) vs `INTERNAL_TOOLS` (system). Self-describing docstrings. Structured returns for UI. |
| **Storage** | S3 | Presigned URLs for direct upload/download. Decoupled from compute. |
| **Local Dev** | LocalStack + Docker | S3 and DynamoDB via LocalStack. OpenSearch via Docker. Same code paths as production. |
| **Build Tool** | Make | Single command interface for frontend and backend. Unified `make dev`, `make test`, etc. simplifies development workflow. |

## Architecture

| Layer | File | Purpose |
|-------|------|---------|
| Entry | `handler.py` | Lambda entry point (HTTP, async jobs, recovery) |
| API | `app.py` | FastAPI routes (`/api/config`, `/api/jobs`, `/api/documents`) |
| Agent | `agent.py` | LangGraph `create_react_agent` + progress callbacks |
| Tools | `tools.py` | `@tool` decorated functions for LLM |
| Jobs | `jobs.py` | DynamoDB job store, async execution |
| Models | `models.py` | Pydantic API contracts |
| Document | `document.py` | Processing pipeline (download → detect → extract → chunk → embed → index) |
| Search | `search.py` | OpenSearch client, embeddings |
| Extract | `extract.py` | Text/OCR (Textract/Tesseract)/Vision extraction |
| LLM | `llm.py` | OpenAI client (GPT-4o vision) |
| Config | `config.py` | Environment variables |
| Storage | `s3.py` | Presigned URLs for upload/download |

## Document Ingestion

All documents are processed and indexed in OpenSearch for semantic search.

| Document Type | Processing | Result |
|---------------|------------|--------|
| Text (PDF, DOCX) | Extract text directly | Index text chunks |
| Document image (scanned PDF, receipt) | Textract OCR → extract text | Index extracted text |
| Non-text image (photo, diagram) | GPT-4o → describe image | Index description |

**Flow:**
1. Upload document to S3
2. Detect document type
3. If text extractable → extract text
4. If document image → Textract OCR → get text
5. If non-text image → GPT-4o → generate description
6. Chunk text/description
7. Generate embeddings (OpenAI)
8. Index in OpenSearch with metadata

## Agent Tools

### 1. Document Processing

Processes and indexes uploaded documents for search.

**Input:** S3 path to uploaded file (PDF, DOCX, image)
**Flow:**
1. Download from S3
2. Detect type (text doc, scanned doc, image)
3. Extract content (direct / OCR / vision AI)
4. Chunk and generate embeddings
5. Index in OpenSearch

**Returns:** Document ID, extraction summary, chunk count

### 2. Search (Default Tool)

Semantic search over indexed documents. This is the default tool the agent uses first.

**Input:** Query string
**Flow:**
1. Generate query embedding
2. k-NN search on OpenSearch
3. Return top-k chunks with scores
4. Score < threshold → suggest web search

### 3. Web Search

Web search fallback (automatically triggered by Search when needed).

**Input:** Search query
**Flow:**
1. Call web search API
2. Parse top 5 results
3. Return snippets with attribution

### 4. Calculator

Expression parser for deterministic calculations.

**Input:** Math expression
**Example:** `sum([45.00, 120.50, 89.99])` → `255.49`

## Agent Flow

The agent uses LangGraph's prebuilt `create_react_agent` which runs a ReAct loop:

1. **LLM Decision** - Claude analyzes the query and decides which tool to call (or respond directly)
2. **Tool Execution** - Runs the selected tool, result returned to LLM
3. **Loop** - LLM decides next action based on tool result (call another tool or synthesize response)
4. **Response** - When LLM has enough information, generates final response

Progress callbacks update DynamoDB at each step for real-time UI updates.

## Job State

The prebuilt ReAct agent manages its own internal state (messages). Job-level state is tracked in DynamoDB:

```python
class Job:
    id: str
    query: str
    status: JobStatus  # pending → processing → completed/failed
    progress: JobProgress  # step, message, percent
    response: str | None
    tool_trace: list[ToolCall]  # for UI visibility
    error: str | None
```

`AgentRunner` class handles progress callbacks (`on_progress`, `on_tool`) that update DynamoDB during execution.

## Risks

| Risk | Mitigation |
|------|------------|
| Vision API latency | Async processing, caching |
| Wrong tool selection | Clear tool descriptions, eval suite |
| Math extraction errors | Validation, confidence thresholds |
