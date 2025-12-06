import uuid
import base64
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from jobs import get_job_store, run_job_async
from models import (
    AppConfig,
    AppInfo,
    CodeExecutionOutput,
    CreateJobRequest,
    CreateJobResponse,
    HealthResponse,
    Job,
    MessagesConfig,
    SaveExecutionRequest,
    SaveExecutionResponse,
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
    "generate_code": "🐍",
}

WELCOME_MESSAGE = """Hi! I'm your AI assistant. I can help you with:

- **Document Processing** — Upload PDFs, images, or scanned documents. I'll extract the text and index them for search.

- **Search** — Ask questions and I'll search your indexed documents for answers.

- **Web Search** — Search the web for current information, news, or topics not in your documents.

- **Calculator** — Perform basic calculations on data (sums, averages, percentages).

- **Code Execution** — Generate charts, export CSV/Excel files, run statistical analysis, and perform complex data transformations. Code runs securely in your browser.

Try asking me something like "What's in my documents?" or "Create a chart of the revenue data" to get started!"""


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


@app.post("/api/jobs/{job_id}/executions", response_model=SaveExecutionResponse)
async def save_execution(job_id: str, request: SaveExecutionRequest):
    from s3 import upload_bytes
    from config import get_config
    
    store = get_job_store()
    job = store.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    execution_id = str(uuid.uuid4())
    config = get_config()
    output_refs: list[CodeExecutionOutput] = []
    chart_data_url: str | None = None
    
    for output in request.outputs:
        output_type = output.get('type', 'file')
        output_format = output.get('format', 'bin')
        output_data = output.get('data', '')
        filename = output.get('filename', f'output.{output_format}')
        
        if output_data:
            try:
                binary_data = base64.b64decode(output_data)
                s3_key = f"executions/{job_id}/{execution_id}/{filename}"
                upload_bytes(binary_data, s3_key, f"application/{output_format}")
                output_refs.append(CodeExecutionOutput(
                    type=output_type,
                    format=output_format,
                    s3_path=f"s3://{config.s3_bucket}/{s3_key}",
                    filename=filename
                ))
            except Exception as e:
                print(f"[WARN] Failed to upload output: {e}")
    
    if request.chart_data:
        if len(request.chart_data) > 10000:  # >10KB, store in S3
            s3_key = f"executions/{job_id}/{execution_id}/chart.json"
            upload_bytes(request.chart_data.encode('utf-8'), s3_key, "application/json")
            chart_data_url = f"s3://{config.s3_bucket}/{s3_key}"
        else:
            chart_data_url = request.chart_data  # Store inline
    
    execution_data = {
        'code': request.code,
        'explanation': request.explanation,
        'success': request.success,
        'result': request.result,
        'stdout': request.stdout,
        'error': request.error,
        'outputs': [o.model_dump() for o in output_refs],
        'chart_data_url': chart_data_url,
        'table_data': request.table_data[:100] if request.table_data else None,  # Limit table data
        'execution_time_ms': request.execution_time_ms
    }
    
    store.save_execution(job_id, execution_id, execution_data)
    
    return SaveExecutionResponse(
        id=execution_id,
        job_id=job_id,
        outputs=output_refs,
        chart_data_url=chart_data_url
    )


@app.get("/api/jobs/{job_id}/executions")
async def get_executions(job_id: str):
    store = get_job_store()
    job = store.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return store.get_executions(job_id)
