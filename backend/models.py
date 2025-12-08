from pydantic import BaseModel, Field
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobProgress(BaseModel):
    step: str = ""
    message: str = ""
    percent: int = 0


class ToolCall(BaseModel):
    tool: str
    input: dict = Field(default_factory=dict)
    output: dict | None = None
    success: bool = True


class Job(BaseModel):
    id: str
    query: str
    status: JobStatus = JobStatus.PENDING
    progress: JobProgress = Field(default_factory=JobProgress)
    response: str | None = None
    tool_trace: list[ToolCall] = Field(default_factory=list)
    error: str | None = None
    created_at: str
    updated_at: str
    started_at: str | None = None
    retry_count: int = 0


class CreateJobRequest(BaseModel):
    query: str
    history: list[dict] = Field(default_factory=list)


class CreateJobResponse(BaseModel):
    job_id: str
    status: JobStatus


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ToolInfo(BaseModel):
    name: str
    description: str
    icon: str


class AppInfo(BaseModel):
    title: str
    subtitle: str


class UploadConfig(BaseModel):
    accept: str
    max_size_mb: int


class MessagesConfig(BaseModel):
    input_placeholder: str
    loading: str
    no_tools: str
    upload_error: str


class AppConfig(BaseModel):
    app: AppInfo
    welcome_message: str
    tools: list[ToolInfo]
    upload: UploadConfig
    messages: MessagesConfig


class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str | None = None


class UploadUrlResponse(BaseModel):
    url: str
    s3_path: str
    key: str
    content_type: str
    expires_in: int
    original_filename: str


class ViewUrlRequest(BaseModel):
    s3_path: str


class ViewUrlResponse(BaseModel):
    url: str
    s3_path: str
    filename: str
    expires_in: int


class DocumentReference(BaseModel):
    document_id: str
    filename: str
    s3_path: str
    score: float
    text: str
    chunk_index: int | None = None


class WebReference(BaseModel):
    title: str
    url: str
    snippet: str


class SearchToolOutput(BaseModel):
    query: str
    documents: list[DocumentReference] = Field(default_factory=list)
    document_count: int = 0
    low_confidence: bool = False
    message: str = ""
    document_id: str | None = None


class WebSearchToolOutput(BaseModel):
    results: list[WebReference] = Field(default_factory=list)


class CalculatorToolOutput(BaseModel):
    result: float | int
    expression: str


class HealthResponse(BaseModel):
    status: str
    services: list[dict]
    timestamp: str


class CodeOutput(BaseModel):
    type: str  # "image" | "file" | "dataframe"
    format: str  # "png" | "csv" | "xlsx" | "json"
    data: str  # base64 encoded
    filename: str | None = None


class CodeGenerationResult(BaseModel):
    code: str
    data: dict
    output_type: str  # "chart" | "file" | "calculation" | "dataframe"
    requires_execution: bool = True
    explanation: str


class ExecutionResult(BaseModel):
    success: bool
    result: dict | list | str | int | float | None = None
    stdout: str = ""
    error: str | None = None
    outputs: list[CodeOutput] = Field(default_factory=list)
    execution_time_ms: int = 0


class CodeExecutionOutput(BaseModel):
    type: str  # "chart" | "image" | "file"
    format: str
    s3_path: str  # S3 path for binary data
    filename: str | None = None


class CodeExecutionRecord(BaseModel):
    id: str
    job_id: str
    code: str
    explanation: str = ""
    success: bool
    result: dict | list | str | int | float | None = None
    stdout: str = ""
    error: str | None = None
    outputs: list[CodeExecutionOutput] = Field(default_factory=list)
    chart_data_url: str | None = None  # S3 path for Plotly JSON
    table_data: list[dict] | None = None  # Small table data inline, large in S3
    execution_time_ms: int = 0
    created_at: str


class SaveExecutionRequest(BaseModel):
    code: str
    explanation: str = ""
    success: bool
    result: dict | list | str | int | float | None = None
    stdout: str = ""
    error: str | None = None
    outputs: list[dict] = Field(default_factory=list)  # Raw output data with base64
    chart_data: str | None = None  # Plotly JSON string
    table_data: list[dict] | None = None
    execution_time_ms: int = 0


class SaveExecutionResponse(BaseModel):
    id: str
    job_id: str
    outputs: list[CodeExecutionOutput] = Field(default_factory=list)
    chart_data_url: str | None = None

