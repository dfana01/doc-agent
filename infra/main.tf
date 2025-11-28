terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix          = "${var.project_name}-${var.environment}"
  lambda_function_name = "${var.project_name}-${var.environment}-agent"
}

# Get current AWS account ID for constructing ARNs
data "aws_caller_identity" "current" {}

resource "random_id" "suffix" {
  byte_length = 4
}

# =============================================================================
# S3 - Private Document Storage with Presigned URL Access
# =============================================================================

resource "aws_s3_bucket" "documents" {
  bucket = "${local.name_prefix}-documents-${random_id.suffix.hex}"

  tags = {
    Name = "${local.name_prefix}-documents"
  }
}

# Block ALL public access
resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS configuration for presigned URL uploads from browser
resource "aws_s3_bucket_cors_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "HEAD"]
    allowed_origins = var.allowed_origins
    expose_headers  = ["ETag", "Content-Length", "Content-Type"]
    max_age_seconds = 3600
  }
}

# Bucket policy - Only allow access via Lambda role (presigned URLs use this role)
resource "aws_s3_bucket_policy" "documents" {
  bucket = aws_s3_bucket.documents.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowLambdaAccess"
        Effect    = "Allow"
        Principal = { AWS = aws_iam_role.lambda.arn }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.documents]
}

# =============================================================================
# DynamoDB - Job Queue
# =============================================================================

resource "aws_dynamodb_table" "jobs" {
  name         = "${local.name_prefix}-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  # Auto-delete completed jobs after 24 hours
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${local.name_prefix}-jobs"
  }
}

# =============================================================================
# S3 - Frontend Static Hosting (via CloudFront)
# =============================================================================

resource "aws_s3_bucket" "frontend" {
  bucket = "${local.name_prefix}-frontend-${random_id.suffix.hex}"

  tags = {
    Name = "${local.name_prefix}-frontend"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# CloudFront - Frontend Distribution
# =============================================================================

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${local.name_prefix}-frontend-oac"
  description                       = "OAC for frontend S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "${local.name_prefix} frontend"

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "S3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  # API origin (proxy to API Gateway)
  origin {
    domain_name = replace(aws_apigatewayv2_api.main.api_endpoint, "https://", "")
    origin_id   = "API-Gateway"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-frontend"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  # API routes go to API Gateway
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "API-Gateway"

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type"]
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "https-only"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }

  # SPA fallback - serve index.html for client-side routing
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "${local.name_prefix}-frontend"
  }
}

# S3 bucket policy for CloudFront access
resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

# =============================================================================
# OpenSearch - Vector Database (Public)
# =============================================================================

resource "aws_opensearch_domain" "main" {
  domain_name    = "${local.name_prefix}-search"
  engine_version = "OpenSearch_2.11"

  cluster_config {
    instance_type  = var.opensearch_instance_type
    instance_count = 1
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 10
    volume_type = "gp3"
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { AWS = aws_iam_role.lambda.arn }
        Action    = "es:*"
        Resource  = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${local.name_prefix}-search/*"
      },
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "es:ESHttp*"
        Resource  = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${local.name_prefix}-search/*"
        Condition = {
          IpAddress = {
            "aws:SourceIp" = var.allowed_dashboard_ips
          }
        }
      }
    ]
  })

  # Wait for service-linked role to be created (if we're managing it)
  depends_on = [aws_iam_service_linked_role.opensearch]

  tags = {
    Name = "${local.name_prefix}-search"
  }

  # OpenSearch can take 10-15 minutes to create
  timeouts {
    create = "30m"
    delete = "30m"
  }
}

# Service-linked role for OpenSearch
# Set create_opensearch_service_role = false if it already exists in your account
resource "aws_iam_service_linked_role" "opensearch" {
  count            = var.create_opensearch_service_role ? 1 : 0
  aws_service_name = "opensearchservice.amazonaws.com"
  description      = "Service-linked role for OpenSearch"

  # If the role already exists, Terraform will error. Set the variable to false instead.
  lifecycle {
    ignore_changes = [description]
  }
}

# =============================================================================
# IAM - Lambda Execution Role
# =============================================================================

resource "aws_iam_role" "lambda" {
  name = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda" {
  name = "${local.name_prefix}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      },
      {
        Sid    = "OpenSearchAccess"
        Effect = "Allow"
        Action = [
          "es:ESHttpGet",
          "es:ESHttpPost",
          "es:ESHttpPut",
          "es:ESHttpDelete"
        ]
        Resource = "${aws_opensearch_domain.main.arn}/*"
      },
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.jobs.arn
      },
      {
        Sid    = "LambdaSelfInvoke"
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.lambda_function_name}"
      },
      {
        Sid    = "TextractAccess"
        Effect = "Allow"
        Action = [
          "textract:DetectDocumentText",
          "textract:AnalyzeDocument"
        ]
        Resource = "*"
      }
    ]
  })
}

# =============================================================================
# Lambda - Agent Function
# =============================================================================

resource "aws_lambda_function" "agent" {
  function_name = local.lambda_function_name
  role          = aws_iam_role.lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = {
      SERVER_ANTHROPIC_API_KEY   = var.anthropic_api_key
      SERVER_OPENAI_API_KEY      = var.openai_api_key
      SERVER_OPENSEARCH_ENDPOINT = aws_opensearch_domain.main.endpoint
      SERVER_OPENSEARCH_INDEX    = "documents"
      SERVER_S3_BUCKET           = aws_s3_bucket.documents.id
      SERVER_AWS_REGION          = var.aws_region
      SERVER_DYNAMODB_JOBS_TABLE = aws_dynamodb_table.jobs.name
      SERVER_AGENT_MODEL         = var.agent_model
      SERVER_EMBEDDING_MODEL     = var.embedding_model
      SERVER_VISION_MODEL        = var.vision_model
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda,
    aws_cloudwatch_log_group.lambda
  ]
}

# Lambda placeholder for initial deployment
data "archive_file" "lambda_placeholder" {
  type        = "zip"
  output_path = "${path.module}/lambda_placeholder.zip"

  source {
    content  = "def lambda_handler(event, context): return {'statusCode': 200, 'body': 'Placeholder'}"
    filename = "handler.py"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.lambda_function_name}"
  retention_in_days = 14
}

# =============================================================================
# API Gateway - HTTP API
# =============================================================================

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = var.allowed_origins
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.agent.invoke_arn
  integration_method = "POST"
}

# Catch-all route - FastAPI handles all routing
resource "aws_apigatewayv2_route" "api" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /api/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agent.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# =============================================================================
# CloudWatch EventBridge - Job Recovery Scheduler
# =============================================================================

# EventBridge rule to trigger job recovery every 5 minutes
resource "aws_cloudwatch_event_rule" "job_recovery" {
  name                = "${local.name_prefix}-job-recovery"
  description         = "Trigger job recovery to handle stale/stuck jobs"
  schedule_expression = "rate(5 minutes)"

  tags = {
    Name = "${local.name_prefix}-job-recovery"
  }
}

# Target: Lambda function
resource "aws_cloudwatch_event_target" "job_recovery_lambda" {
  rule      = aws_cloudwatch_event_rule.job_recovery.name
  target_id = "JobRecoveryLambda"
  arn       = aws_lambda_function.agent.arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "eventbridge_job_recovery" {
  statement_id  = "AllowEventBridgeJobRecovery"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agent.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.job_recovery.arn
}

# =============================================================================
# Outputs
# =============================================================================

output "frontend_url" {
  description = "CloudFront distribution URL for frontend"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "api_url" {
  description = "API Gateway URL (also accessible via CloudFront /api/*)"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "s3_documents_bucket" {
  description = "S3 bucket for documents (private, use presigned URLs)"
  value       = aws_s3_bucket.documents.id
}

output "s3_frontend_bucket" {
  description = "S3 bucket for frontend static files"
  value       = aws_s3_bucket.frontend.id
}

output "opensearch_endpoint" {
  description = "OpenSearch domain endpoint (public)"
  value       = aws_opensearch_domain.main.endpoint
}

output "opensearch_dashboard" {
  description = "OpenSearch dashboard URL"
  value       = "https://${aws_opensearch_domain.main.endpoint}/_dashboards/"
}

output "lambda_function_name" {
  description = "Lambda function name for code deployment"
  value       = aws_lambda_function.agent.function_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for cache invalidation"
  value       = aws_cloudfront_distribution.frontend.id
}

output "dynamodb_jobs_table" {
  description = "DynamoDB table name for jobs"
  value       = aws_dynamodb_table.jobs.name
}

output "agent_model" {
  description = "Anthropic model used by the agent"
  value       = var.agent_model
}

output "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  value       = var.lambda_memory_size
}
