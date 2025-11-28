# AI Agent

LangGraph-based multi-tool agent for document Q&A with tool visibility.

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- make
- AWS CLI (for local data cleanup and deployment)
- (Optional) Tesseract OCR for document processing
- (Optional) Terraform >= 1.0 for AWS deployment

### Installation
```bash
make env-setup    # Create .env from template
make install      # Install Python & Node dependencies
```

### Configuration

Edit `.env` with your API keys. See [`env.example`](./env.example) for all options and documentation.

> **Note:** Local development defaults are pre-configured. You only need to add your API keys.

## Quick Start

**One command to run everything:**
```bash
make dev
```

This starts Docker services + backend + frontend with hot reload.

| Service     | URL                        |
|-------------|----------------------------|
| Frontend    | http://localhost:3000     |
| Backend API | http://localhost:8000/     |
| API Docs    | http://localhost:8000/docs |

## Local Development (3 Terminals)

For more control, run services separately in 3 terminals:

### Terminal 1: Infrastructure (LocalStack + OpenSearch)
```bash
make services-up
```
| Service              | URL                       |
|----------------------|---------------------------|
| LocalStack (S3/DynamoDB) | http://localhost:4566 |
| S3 Browser           | http://localhost:8080     |
| DynamoDB Admin       | http://localhost:8001     |
| OpenSearch           | http://localhost:9200     |
| OpenSearch Dashboards| http://localhost:5601     |

### Terminal 2: Backend
```bash
make dev-backend
```
Backend runs at http://localhost:8080/ with hot reload.

### Terminal 3: Frontend
```bash
make dev-frontend
```
Frontend runs at http://localhost:3000/ with hot reload.

**Stop infrastructure:**
```bash
make services-down
```

**Clear local data:**
```bash
make clean-data
```

## Deploy to AWS

### Step 1: Setup

**Prerequisites:**
- AWS CLI configured with appropriate credentials
- Terraform >= 1.0

```bash
make infra-setup    # Create terraform.tfvars from template
```

Edit `infra/terraform.tfvars` with your values. See [`infra/terraform.tfvars.example`](./infra/terraform.tfvars.example) for all options and documentation.

### Step 2: Pre-Review

Before deploying, review what will be created:

```bash
make infra-init     # Initialize Terraform (downloads providers)
make infra-plan     # Preview infrastructure changes
```

Check the plan output

### Step 3: Infrastructure

Apply the infrastructure:

```bash
make infra-apply    # Create AWS resources
```

Type `yes` when prompted to confirm.

### Step 4: Application Deployment

Build and deploy the application code:

```bash
make deploy         # Build and deploy backend + frontend
```

This command:
1. Builds Lambda deployment package (`backend/lambda.zip`)
2. Builds frontend (`frontend/dist/`)
3. Updates Lambda function code
4. Syncs frontend to S3
5. Invalidates CloudFront cache

### Step 5: Post-Review

Verify the deployment:

```bash
make infra-output   # Get CloudFront URL and other outputs
```

**Test your deployment:**
1. Visit the CloudFront URL in your browser
2. Check the API health: `https://<api-url>/health`
3. Type "system health check" in the chat to run diagnostics

**Troubleshooting:**
- Check CloudWatch logs for Lambda errors
- Verify environment variables in Lambda configuration
- Ensure API keys are correctly set

**Tear down (when needed):**
```bash
make infra-destroy  # Destroy all AWS resources
```

## Available Tools

| Tool                  | Description                              |
|-----------------------|------------------------------------------|
| `search`              | Semantic search over indexed documents   |
| `web_search`          | Web search fallback                      |
| `document_processing` | Process & index documents (OCR/vision)   |
| `calculator`          | Perform calculations                     |

## All Commands

Run `make help` for the full list of available commands.
