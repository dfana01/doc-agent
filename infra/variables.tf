variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ai-agent"
}

variable "environment" {
  description = "Environment (dev, prod)"
  type        = string
  default     = "dev"
}

variable "opensearch_instance_type" {
  description = "OpenSearch instance type"
  type        = string
  default     = "t3.small.search"
}

variable "allowed_origins" {
  description = "Allowed origins for CORS (S3 presigned uploads and API)"
  type        = list(string)
  default     = ["*"]
}

# Secrets (pass via terraform.tfvars or env vars)
variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "create_opensearch_service_role" {
  description = "Create OpenSearch service-linked role (set to false if it already exists in your AWS account)"
  type        = bool
  default     = true
}

# Model Configuration
variable "agent_model" {
  description = "Anthropic model for the agent (e.g., claude-sonnet-4-20250514)"
  type        = string
  default     = "claude-sonnet-4-20250514"
}

variable "embedding_model" {
  description = "OpenAI model for embeddings (e.g., text-embedding-3-small)"
  type        = string
  default     = "text-embedding-3-small"
}

variable "vision_model" {
  description = "OpenAI model for vision/OCR (e.g., gpt-4o)"
  type        = string
  default     = "gpt-4o"
}

# Lambda Configuration
variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 1024
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 900
}

variable "allowed_dashboard_ips" {
  description = "IP addresses allowed to access OpenSearch Dashboard (e.g., ['YOUR_IP/32'])"
  type        = list(string)
}
