import os
from dataclasses import dataclass


def get_env(key: str, default: str = "") -> str:
    return os.getenv(f"SERVER_{key}", os.getenv(key, default))


@dataclass
class Config:
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    
    agent_model: str = "claude-sonnet-4-20250514"
    code_generation_model: str = "claude-sonnet-4-20250514"  # For Python code generation
    embedding_model: str = "text-embedding-3-small"
    openai_model: str = "gpt-4o"  # Used for vision tasks
    
    aws_region: str = "us-east-1"
    
    opensearch_endpoint: str = ""
    opensearch_index: str = "documents"
    
    s3_bucket: str = ""
    s3_endpoint: str = ""
    
    dynamodb_jobs_table: str = "ai-agent-jobs"
    dynamodb_endpoint: str = ""
    
    textract_endpoint: str = ""
    
    @property
    def is_local(self) -> bool:
        return bool(self.s3_endpoint)


def get_config() -> Config:
    return Config(
        anthropic_api_key=get_env("ANTHROPIC_API_KEY"),
        openai_api_key=get_env("OPENAI_API_KEY"),
        agent_model=get_env("AGENT_MODEL", "claude-sonnet-4-20250514"),
        code_generation_model=get_env("CODE_GENERATION_MODEL", "claude-sonnet-4-20250514"),
        embedding_model=get_env("EMBEDDING_MODEL", "text-embedding-3-small"),
        openai_model=get_env("OPENAI_MODEL", "gpt-4o"),
        aws_region=get_env("AWS_REGION", "us-east-1"),
        opensearch_endpoint=get_env("OPENSEARCH_ENDPOINT"),
        opensearch_index=get_env("OPENSEARCH_INDEX", "documents"),
        s3_bucket=get_env("S3_BUCKET"),
        s3_endpoint=get_env("S3_ENDPOINT"),
        dynamodb_jobs_table=get_env("DYNAMODB_JOBS_TABLE", "ai-agent-jobs"),
        dynamodb_endpoint=get_env("DYNAMODB_ENDPOINT"),
        textract_endpoint=get_env("TEXTRACT_ENDPOINT"),
    )


def get_s3_client():
    import boto3
    
    config = get_config()
    
    if config.s3_endpoint:
        return boto3.client(
            "s3",
            endpoint_url=config.s3_endpoint,
            region_name=config.aws_region,
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
    else:
        return boto3.client("s3", region_name=config.aws_region)
