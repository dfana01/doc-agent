import os
import uuid
import json
import threading
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum

from config import get_config


STALE_JOB_TIMEOUT_SECONDS = 900
MAX_RETRIES = 3


def is_lambda_environment() -> bool:
    return bool(os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobProgress:
    step: str = ""
    message: str = ""
    percent: int = 0


@dataclass
class Job:
    id: str
    query: str
    status: JobStatus = JobStatus.PENDING
    progress: JobProgress = field(default_factory=JobProgress)
    response: str | None = None
    tool_trace: list = field(default_factory=list)
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: str | None = None
    retry_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "query": self.query,
            "status": self.status.value,
            "progress": asdict(self.progress),
            "response": self.response,
            "tool_trace": self.tool_trace,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "retry_count": self.retry_count,
        }


def _convert(obj, from_type, to_fn):
    if isinstance(obj, from_type):
        return to_fn(obj)
    if isinstance(obj, dict):
        return {k: _convert(v, from_type, to_fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert(item, from_type, to_fn) for item in obj]
    return obj


def _to_decimal(obj):
    return _convert(obj, float, lambda x: Decimal(str(x)))


def _from_decimal(obj):
    return _convert(obj, Decimal, lambda x: int(x) if x % 1 == 0 else float(x))


class DynamoDBJobStore:
    def __init__(self):
        config = get_config()
        self.table_name = config.dynamodb_jobs_table
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            import boto3
            config = get_config()
            if config.dynamodb_endpoint:
                self._client = boto3.resource(
                    'dynamodb',
                    endpoint_url=config.dynamodb_endpoint,
                    region_name=config.aws_region,
                    aws_access_key_id='test',
                    aws_secret_access_key='test'
                )
            else:
                self._client = boto3.resource('dynamodb', region_name=config.aws_region)
        return self._client
    
    @property
    def table(self):
        return self.client.Table(self.table_name)
    
    def create(self, query: str, history: list | None = None) -> Job:
        job = Job(id=str(uuid.uuid4()), query=query)
        self.table.put_item(Item={
            'id': job.id,
            'query': job.query,
            'status': job.status.value,
            'progress': asdict(job.progress),
            'response': None,
            'tool_trace': [],
            'error': None,
            'history': json.dumps(history or []),
            'created_at': job.created_at,
            'updated_at': job.updated_at,
            'started_at': None,
            'retry_count': 0,
        })
        return job
    
    def get(self, job_id: str) -> Job | None:
        item = self.table.get_item(Key={'id': job_id}).get('Item')
        if not item:
            return None
        return Job(
            id=item['id'],
            query=item['query'],
            status=JobStatus(item['status']),
            progress=JobProgress(**_from_decimal(item.get('progress', {}))),
            response=item.get('response'),
            tool_trace=_from_decimal(item.get('tool_trace', [])),
            error=item.get('error'),
            created_at=item['created_at'],
            updated_at=item['updated_at'],
            started_at=item.get('started_at'),
            retry_count=int(item.get('retry_count', 0)),
        )
    
    def get_history(self, job_id: str) -> list:
        item = self.table.get_item(Key={'id': job_id}).get('Item')
        return json.loads(item.get('history', '[]')) if item else []
    
    def update(self, job: Job) -> None:
        job.updated_at = datetime.utcnow().isoformat()
        self.table.update_item(
            Key={'id': job.id},
            UpdateExpression='SET #status = :status, progress = :progress, #response = :response, tool_trace = :trace, #error = :error, updated_at = :updated, started_at = :started, retry_count = :retry',
            ExpressionAttributeNames={'#status': 'status', '#response': 'response', '#error': 'error'},
            ExpressionAttributeValues={
                ':status': job.status.value,
                ':progress': asdict(job.progress),
                ':response': job.response,
                ':trace': _to_decimal(job.tool_trace),
                ':error': job.error,
                ':updated': job.updated_at,
                ':started': job.started_at,
                ':retry': job.retry_count,
            }
        )
    
    def find_stale_jobs(self) -> list[Job]:
        response = self.table.scan(
            FilterExpression='#status = :processing',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':processing': JobStatus.PROCESSING.value}
        )
        cutoff = datetime.utcnow() - timedelta(seconds=STALE_JOB_TIMEOUT_SECONDS)
        
        def is_stale(item: dict) -> bool:
            started = item.get('started_at')
            if not started:
                return True
            try:
                return datetime.fromisoformat(started) < cutoff
            except (ValueError, TypeError):
                return True
        
        return [self.get(item['id']) for item in response.get('Items', []) if is_stale(item)]


_job_store: DynamoDBJobStore | None = None


def get_job_store() -> DynamoDBJobStore:
    global _job_store
    if _job_store is None:
        _job_store = DynamoDBJobStore()
    return _job_store


def run_job_async(job_id: str) -> None:
    if is_lambda_environment():
        _run_job_lambda(job_id)
    else:
        _run_job_local(job_id)


def _run_job_lambda(job_id: str) -> None:
    import boto3
    function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
    if function_name:
        boto3.client('lambda').invoke(
            FunctionName=function_name,
            InvocationType='Event',
            Payload=json.dumps({'job_execution': True, 'job_id': job_id})
        )


def _run_job_local(job_id: str) -> None:
    def run():
        try:
            execute_job(job_id)
        except Exception as e:
            import traceback
            print(f"[JOB ERROR] Job {job_id} failed:", flush=True)
            traceback.print_exc()
            _mark_job_failed(job_id, str(e))
    
    threading.Thread(target=run, daemon=True).start()


def _mark_job_failed(job_id: str, error: str) -> None:
    try:
        store = get_job_store()
        job = store.get(job_id)
        if job and job.status != JobStatus.COMPLETED:
            job.status = JobStatus.FAILED
            job.error = error
            job.progress = JobProgress(step="error", message=error, percent=0)
            store.update(job)
    except Exception:
        pass


def execute_job(job_id: str) -> None:
    from agent import run_agent_with_progress
    
    store = get_job_store()
    job = store.get(job_id)
    if not job:
        return
    
    job.status = JobStatus.PROCESSING
    job.started_at = datetime.utcnow().isoformat()
    job.progress = JobProgress(step="starting", message="Starting agent...", percent=5)
    job.tool_trace = []
    store.update(job)
    
    def on_progress(step: str, message: str, percent: int):
        job.progress = JobProgress(step=step, message=message, percent=percent)
        store.update(job)
    
    def on_tool(tool_call: dict):
        job.tool_trace.append(tool_call)
        store.update(job)
    
    try:
        history = store.get_history(job_id)
        result = run_agent_with_progress(job.query, history, on_progress, on_tool)
        job.status = JobStatus.COMPLETED
        job.response = result["response"]
        job.tool_trace = result["tool_trace"]
        job.error = result.get("error")
        job.progress = JobProgress(step="done", message="Complete", percent=100)
        store.update(job)
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.progress = JobProgress(step="error", message=str(e), percent=0)
        store.update(job)


def recover_stale_jobs() -> dict:
    store = get_job_store()
    stale_jobs = store.find_stale_jobs()
    result = {"found": len(stale_jobs), "retried": 0, "failed": 0, "jobs": []}
    
    for job in stale_jobs:
        if job.retry_count < MAX_RETRIES:
            job.retry_count += 1
            job.status = JobStatus.PENDING
            job.started_at = None
            job.progress = JobProgress(step="retry", message=f"Retrying (attempt {job.retry_count})", percent=0)
            job.error = None
            store.update(job)
            run_job_async(job.id)
            result["retried"] += 1
            result["jobs"].append({"id": job.id, "action": "retried", "attempt": job.retry_count})
        else:
            job.status = JobStatus.FAILED
            job.error = f"Job failed after {MAX_RETRIES} retry attempts"
            job.progress = JobProgress(step="error", message="Max retries exceeded", percent=0)
            store.update(job)
            result["failed"] += 1
            result["jobs"].append({"id": job.id, "action": "failed", "reason": "max_retries_exceeded"})
    
    return result
