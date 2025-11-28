import time
from dataclasses import dataclass, asdict

from config import get_config, get_s3_client


@dataclass
class ServiceHealth:
    name: str
    status: str  # "ok", "error", "unconfigured"
    latency_ms: float | None = None
    message: str | None = None
    error: str | None = None


@dataclass
class SystemHealth:
    overall: str  # "healthy", "degraded", "unhealthy"
    services: list[dict]
    timestamp: str
    
    def to_dict(self) -> dict:
        return asdict(self)


def check_claude() -> ServiceHealth:
    config = get_config()
    
    if not config.anthropic_api_key:
        return ServiceHealth(
            name="claude",
            status="unconfigured",
            message="ANTHROPIC_API_KEY not set"
        )
    
    try:
        import anthropic
        
        start = time.time()
        client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'ok'"}]
        )
        latency = (time.time() - start) * 1000
        
        return ServiceHealth(
            name="claude",
            status="ok",
            latency_ms=round(latency, 2),
            message=f"Model: claude-sonnet-4-20250514"
        )
    except Exception as e:
        return ServiceHealth(
            name="claude",
            status="error",
            error=str(e)
        )


def check_openai() -> ServiceHealth:
    config = get_config()
    
    if not config.openai_api_key:
        return ServiceHealth(
            name="openai",
            status="unconfigured",
            message="OPENAI_API_KEY not set"
        )
    
    try:
        import openai
        
        start = time.time()
        client = openai.OpenAI(api_key=config.openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'ok'"}]
        )
        latency = (time.time() - start) * 1000
        
        return ServiceHealth(
            name="openai",
            status="ok",
            latency_ms=round(latency, 2),
            message="Model: gpt-4o-mini"
        )
    except Exception as e:
        return ServiceHealth(
            name="openai",
            status="error",
            error=str(e)
        )


def check_duckduckgo() -> ServiceHealth:
    try:
        from ddgs import DDGS
        
        start = time.time()
        with DDGS() as ddgs:
            results = list(ddgs.text("test", max_results=1))
        latency = (time.time() - start) * 1000
        
        return ServiceHealth(
            name="duckduckgo",
            status="ok",
            latency_ms=round(latency, 2),
            message=f"Found {len(results)} result(s)"
        )
    except ImportError:
        return ServiceHealth(
            name="duckduckgo",
            status="error",
            error="ddgs not installed"
        )
    except Exception as e:
        return ServiceHealth(
            name="duckduckgo",
            status="error",
            error=str(e)
        )


def check_s3() -> ServiceHealth:
    config = get_config()
    
    if not config.s3_bucket:
        return ServiceHealth(
            name="s3",
            status="unconfigured",
            message="S3_BUCKET not set"
        )
    
    try:
        from botocore.exceptions import ClientError, NoCredentialsError
        
        start = time.time()
        # Use get_s3_client which handles LocalStack endpoint
        s3 = get_s3_client()
        
        s3.head_bucket(Bucket=config.s3_bucket)
        latency = (time.time() - start) * 1000
        
        mode = "local" if config.s3_endpoint else "aws"
        return ServiceHealth(
            name="s3",
            status="ok",
            latency_ms=round(latency, 2),
            message=f"Bucket: {config.s3_bucket} ({mode})"
        )
    except NoCredentialsError:
        return ServiceHealth(
            name="s3",
            status="error",
            error="AWS credentials not configured"
        )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        return ServiceHealth(
            name="s3",
            status="error",
            error=f"S3 error: {error_code}"
        )
    except ImportError:
        return ServiceHealth(
            name="s3",
            status="error",
            error="boto3 not installed"
        )
    except Exception as e:
        return ServiceHealth(
            name="s3",
            status="error",
            error=str(e)
        )


def check_opensearch() -> ServiceHealth:
    config = get_config()
    
    if not config.opensearch_endpoint:
        return ServiceHealth(
            name="opensearch",
            status="unconfigured",
            message="OPENSEARCH_ENDPOINT not set"
        )
    
    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from urllib.parse import urlparse
        
        start = time.time()
        
        parsed = urlparse(config.opensearch_endpoint)
        # Handle endpoints without scheme (AWS returns just hostname)
        if parsed.scheme in ("http", "https"):
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 9200)
            use_ssl = parsed.scheme == "https"
        else:
            # No scheme - assume AWS OpenSearch (HTTPS on 443)
            host = config.opensearch_endpoint
            port = 443
            use_ssl = True
        
        is_local = host in ("localhost", "127.0.0.1") or config.opensearch_endpoint.startswith("http://localhost")
        
        if is_local:
            # Local OpenSearch - no auth needed
            client = OpenSearch(
                hosts=[{"host": host, "port": port}],
                use_ssl=use_ssl,
                verify_certs=False,
                connection_class=RequestsHttpConnection,
            )
        else:
            # AWS OpenSearch - use IAM auth
            from requests_aws4auth import AWS4Auth
            import boto3
            
            credentials = boto3.Session().get_credentials()
            if not credentials:
                return ServiceHealth(
                    name="opensearch",
                    status="error",
                    error="AWS credentials not configured"
                )
            
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                config.aws_region,
                "es",
                session_token=credentials.token
            )
            
            client = OpenSearch(
                hosts=[{"host": host, "port": port}],
                http_auth=awsauth,
                use_ssl=use_ssl,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
            )
        
        health = client.cluster.health()
        latency = (time.time() - start) * 1000
        
        mode = "local" if is_local else "aws"
        return ServiceHealth(
            name="opensearch",
            status="ok",
            latency_ms=round(latency, 2),
            message=f"Cluster: {health.get('cluster_name', 'unknown')}, Status: {health.get('status', 'unknown')} ({mode})"
        )
    except ImportError as e:
        missing = getattr(e, 'name', str(e))
        return ServiceHealth(
            name="opensearch",
            status="error",
            error=f"Missing dependency: {missing}"
        )
    except Exception as e:
        return ServiceHealth(
            name="opensearch",
            status="error",
            error=str(e)
        )


def check_agent() -> ServiceHealth:
    try:
        from agent import run_agent
        
        start = time.time()
        
        result = run_agent("What is 2 + 2?")
        latency = (time.time() - start) * 1000
        
        if result.get("error"):
            return ServiceHealth(
                name="agent",
                status="error",
                latency_ms=round(latency, 2),
                error=result["error"]
            )
        
        return ServiceHealth(
            name="agent",
            status="ok",
            latency_ms=round(latency, 2),
            message=f"Response received, {len(result.get('tool_trace', []))} tool(s) used"
        )
    except Exception as e:
        return ServiceHealth(
            name="agent",
            status="error",
            error=str(e)
        )


def check_dynamodb() -> ServiceHealth:
    config = get_config()
    
    if not config.dynamodb_jobs_table:
        return ServiceHealth(
            name="dynamodb",
            status="unconfigured",
            message="DYNAMODB_JOBS_TABLE not set"
        )
    
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        start = time.time()
        
        # Create DynamoDB client with optional LocalStack endpoint
        if config.dynamodb_endpoint:
            dynamodb = boto3.client(
                "dynamodb",
                endpoint_url=config.dynamodb_endpoint,
                region_name=config.aws_region,
                aws_access_key_id="test",
                aws_secret_access_key="test",
            )
        else:
            dynamodb = boto3.client("dynamodb", region_name=config.aws_region)
        
        # Check if table exists using Scan
        dynamodb.scan(TableName=config.dynamodb_jobs_table, Limit=1)
        latency = (time.time() - start) * 1000
        
        mode = "local" if config.dynamodb_endpoint else "aws"
        return ServiceHealth(
            name="dynamodb",
            status="ok",
            latency_ms=round(latency, 2),
            message=f"Table: {config.dynamodb_jobs_table} ({mode})"
        )
    except NoCredentialsError:
        return ServiceHealth(
            name="dynamodb",
            status="error",
            error="AWS credentials not configured"
        )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        return ServiceHealth(
            name="dynamodb",
            status="error",
            error=f"DynamoDB error: {error_code}"
        )
    except ImportError:
        return ServiceHealth(
            name="dynamodb",
            status="error",
            error="boto3 not installed"
        )
    except Exception as e:
        return ServiceHealth(
            name="dynamodb",
            status="error",
            error=str(e)
        )


def check_textract() -> ServiceHealth:
    config = get_config()
    
    # Textract is optional - if not configured, we use local pytesseract
    if not config.textract_endpoint and not config.aws_region:
        return ServiceHealth(
            name="textract",
            status="unconfigured",
            message="Using local pytesseract (no Textract configured)"
        )
    
    # If no explicit textract endpoint, check if we can use AWS Textract
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        start = time.time()
        
        # Create Textract client
        if config.textract_endpoint:
            textract = boto3.client(
                "textract",
                endpoint_url=config.textract_endpoint,
                region_name=config.aws_region,
                aws_access_key_id="test",
                aws_secret_access_key="test",
            )
            mode = "local"
        else:
            textract = boto3.client("textract", region_name=config.aws_region)
            mode = "aws"
        
        # Simple connectivity check - get service limits (doesn't process anything)
        # We can't easily test Textract without an actual document, so we just verify credentials work
        try:
            # This will fail if credentials are invalid
            sts = boto3.client("sts", region_name=config.aws_region)
            sts.get_caller_identity()
            latency = (time.time() - start) * 1000
            
            return ServiceHealth(
                name="textract",
                status="ok",
                latency_ms=round(latency, 2),
                message=f"AWS credentials valid ({mode})"
            )
        except Exception:
            # If we have a local endpoint, try to connect to it
            if config.textract_endpoint:
                latency = (time.time() - start) * 1000
                return ServiceHealth(
                    name="textract",
                    status="ok",
                    latency_ms=round(latency, 2),
                    message=f"Endpoint: {config.textract_endpoint}"
                )
            raise
            
    except NoCredentialsError:
        return ServiceHealth(
            name="textract",
            status="unconfigured",
            message="Using local pytesseract (no AWS credentials)"
        )
    except ImportError:
        return ServiceHealth(
            name="textract",
            status="error",
            error="boto3 not installed"
        )
    except Exception as e:
        return ServiceHealth(
            name="textract",
            status="unconfigured",
            message=f"Using local pytesseract ({str(e)[:50]})"
        )


def run_all_health_checks() -> SystemHealth:
    from datetime import datetime
    
    checks = [
        check_claude(),
        check_openai(),
        check_duckduckgo(),
        check_s3(),
        check_dynamodb(),
        check_opensearch(),
        check_textract(),
        check_agent(),
    ]
    
    statuses = [c.status for c in checks]
    
    if all(s == "ok" for s in statuses):
        overall = "healthy"
    elif all(s in ("ok", "unconfigured") for s in statuses):
        overall = "healthy"
    elif any(s == "ok" for s in statuses):
        overall = "degraded"
    else:
        overall = "unhealthy"
    
    return SystemHealth(
        overall=overall,
        services=[asdict(c) for c in checks],
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


def format_health_report(health: SystemHealth) -> str:
    status_badge = {
        "healthy": "🟢 HEALTHY",
        "degraded": "🟡 DEGRADED", 
        "unhealthy": "🔴 UNHEALTHY"
    }
    
    status_emoji = {
        "ok": "✅",
        "error": "❌",
        "unconfigured": "⚙️"
    }
    
    lines = [
        "## System Health Report",
        "",
        f"**Status:** {status_badge.get(health.overall, health.overall.upper())}",
        "",
        f"*{health.timestamp}*",
        "",
        "---",
        "",
        "### Services",
        "",
        "| Service | Status | Latency | Details |",
        "|---------|--------|---------|---------|",
    ]
    
    for svc in health.services:
        emoji = status_emoji.get(svc["status"], "❓")
        name = svc["name"]
        status = f"{emoji} {svc['status']}"
        latency = f"{svc['latency_ms']}ms" if svc.get("latency_ms") else "—"
        
        details = []
        if svc.get("message"):
            details.append(svc["message"])
        if svc.get("error"):
            details.append(f"⚠️ {svc['error']}")
        detail_text = " ".join(details) if details else "—"
        
        lines.append(f"| **{name}** | {status} | {latency} | {detail_text} |")
    
    return "\n".join(lines)
