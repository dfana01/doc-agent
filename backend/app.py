from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from jobs import get_job_store, run_job_async
from models import (
    AppConfig,
    AppInfo,
    CreateJobRequest,
    CreateJobResponse,
    HealthResponse,
    Job,
    MessagesConfig,
    ToolInfo,
    UploadConfig,
    UploadUrlRequest,
    UploadUrlResponse,
    ViewUrlRequest,
    ViewUrlResponse,
)

app = FastAPI(title="AI Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


TOOL_ICONS = {
    "search": "🔍",
    "web_search": "🌐",
    "document_processing": "📄",
    "calculator": "🧮",
}

WELCOME_MESSAGE = """Hi! I'm your AI assistant. I can help you with:

- **Document Processing** — Upload PDFs, images, or scanned documents. I'll extract the text and index them for search.

- **Search** — Ask questions and I'll search your indexed documents for answers.

- **Web Search** — Search the web for current information, news, or topics not in your documents.

- **Calculator** — Perform calculations on data (sums, averages, percentages, etc).

Try asking me something like "What's in my documents?" or upload a file to get started!"""


@app.get("/api/config", response_model=AppConfig)
async def get_config():
    from tools import AGENT_TOOLS

    return AppConfig(
        app=AppInfo(
            title="AI Agent",
            subtitle="Document Q&A with tool visibility",
        ),
        welcome_message=WELCOME_MESSAGE,
        tools=[
            ToolInfo(
                name=tool.name,
                description=tool.description,
                icon=TOOL_ICONS.get(tool.name, "🔧"),
            )
            for tool in AGENT_TOOLS
        ],
        upload=UploadConfig(
            accept=".pdf,.doc,.docx,.txt,.md,.png,.jpg,.jpeg,.gif,.webp",
            max_size_mb=10,
        ),
        messages=MessagesConfig(
            input_placeholder="Type your message... (Shift+Enter for new line)",
            loading="Thinking...",
            no_tools="No tools used yet",
            upload_error="Upload failed",
        ),
    )


@app.get("/api/config/health", response_model=HealthResponse)
async def health():
    from health import run_all_health_checks

    health_result = run_all_health_checks()

    return HealthResponse(
        status=health_result.overall,
        services=health_result.services,
        timestamp=health_result.timestamp,
    )


@app.post("/api/jobs", response_model=CreateJobResponse)
async def create_job(request: CreateJobRequest):
    store = get_job_store()
    job = store.create(request.query, request.history)

    run_job_async(job.id)

    return CreateJobResponse(
        job_id=job.id,
        status=job.status,
    )


@app.get("/api/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str):
    store = get_job_store()
    job = store.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@app.post("/api/documents/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(request: UploadUrlRequest):
    from s3 import upload_url

    try:
        result = upload_url(request.filename, request.content_type)
        return UploadUrlResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/documents/view-url", response_model=ViewUrlResponse)
async def get_view_url(request: ViewUrlRequest):
    from s3 import view_url

    try:
        result = view_url(request.s3_path)
        return ViewUrlResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
