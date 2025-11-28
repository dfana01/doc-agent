.PHONY: install dev dev-backend dev-frontend build deploy clean help

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Setup

install:
	@echo "Installing dependencies..."
	@if ! command -v tesseract &> /dev/null; then \
		echo "Installing Tesseract OCR..."; \
		if [ "$$(uname)" = "Darwin" ]; then brew install tesseract; \
		elif [ -f /etc/debian_version ]; then sudo apt-get update && sudo apt-get install -y tesseract-ocr; \
		else echo "Please install Tesseract OCR: https://github.com/tesseract-ocr/tesseract"; fi \
	fi
	cd backend && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt -q
	cd frontend && npm install --silent
	@echo "Done!"

env-setup:
	@if [ ! -f .env ]; then cp env.example .env && echo "Created .env - add your API keys"; else echo ".env exists"; fi

# Development

dev: services-up
	@echo ""
	@echo "🚀 Starting development servers..."
	@echo "   Backend:  http://localhost:8000"
	@echo "   Frontend: http://localhost:3000"
	@echo ""
	@trap 'kill 0' EXIT; \
	(cd backend && . venv/bin/activate && python local.py) & \
	(cd frontend && npm run dev) & \
	wait

dev-backend:
	@echo "🔧 Backend: http://localhost:8000 (hot reload enabled)"
	cd backend && . venv/bin/activate && python local.py

dev-frontend:
	@echo "🎨 Frontend: http://localhost:3000 (hot reload enabled)"
	cd frontend && npm run dev

# Local Services (Docker)

services-up:
	docker compose up -d
	@echo ""
	@echo "✅ LocalStack (S3/DynamoDB): http://localhost:4566"
	@echo "✅ S3 Browser:               http://localhost:8080"
	@echo "✅ DynamoDB Admin:           http://localhost:8001"
	@echo "✅ OpenSearch:               http://localhost:9200"
	@echo "✅ OpenSearch Dashboards:    http://localhost:5601"
	@echo ""

services-down:
	docker compose down

clean-data:
	@aws --endpoint-url=http://localhost:4566 s3 rm s3://ai-agent-documents --recursive 2>/dev/null || true
	@curl -s -X DELETE "http://localhost:9200/documents" 2>/dev/null || true
	@aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name ai-agent-jobs --attributes-to-get id --query 'Items[*].id.S' --output text 2>/dev/null | tr '\t' '\n' | while read id; do [ -n "$$id" ] && aws --endpoint-url=http://localhost:4566 dynamodb delete-item --table-name ai-agent-jobs --key "{\"id\": {\"S\": \"$$id\"}}" 2>/dev/null; done || true
	@echo "Local data cleared"

# Build & Deploy

build:
	@echo "Building..."
	@rm -rf backend/dist backend/lambda.zip
	@mkdir -p backend/dist
	cd backend && . venv/bin/activate && \
		pip install -r requirements-deploy.txt -t dist/ -q \
			--platform manylinux2014_x86_64 --implementation cp --python-version 3.11 --only-binary=:all: && \
		cp *.py dist/ && cd dist && \
		find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
		find . -type d -name '*.dist-info' -exec rm -rf {} + 2>/dev/null || true && \
		zip -rq ../lambda.zip .
	cd frontend && npm run build
	@echo "Build complete: backend/lambda.zip, frontend/dist/"

deploy: build
	@FUNCTION_NAME=$$(cd infra && terraform output -raw lambda_function_name 2>/dev/null); \
	BUCKET=$$(cd infra && terraform output -raw s3_frontend_bucket 2>/dev/null); \
	DIST_ID=$$(cd infra && terraform output -raw cloudfront_distribution_id 2>/dev/null); \
	if [ -z "$$FUNCTION_NAME" ] || [ -z "$$BUCKET" ]; then echo "Run 'make infra-apply' first"; exit 1; fi; \
	aws lambda update-function-code --function-name $$FUNCTION_NAME --zip-file fileb://backend/lambda.zip --region $${AWS_REGION:-us-east-1} --no-cli-pager > /dev/null && \
	aws s3 sync frontend/dist/ s3://$$BUCKET/ --delete --region $${AWS_REGION:-us-east-1} --no-cli-pager > /dev/null && \
	[ -n "$$DIST_ID" ] && aws cloudfront create-invalidation --distribution-id $$DIST_ID --paths "/*" --no-cli-pager > /dev/null; \
	echo "Deployed! URL: $$(cd infra && terraform output -raw frontend_url 2>/dev/null)"

# Infrastructure

infra-setup:
	@if [ ! -f infra/terraform.tfvars ]; then cp infra/terraform.tfvars.example infra/terraform.tfvars && echo "Created infra/terraform.tfvars - add your values"; else echo "terraform.tfvars exists"; fi

infra-init:
	cd infra && terraform init

infra-plan:
	cd infra && terraform plan

infra-apply:
	cd infra && terraform apply

infra-destroy:
	cd infra && terraform destroy

infra-output:
	@cd infra && terraform output

# Utilities

generate-types:
	cd backend && . venv/bin/activate && PYTHONPATH=. pydantic2ts --module models --output ../frontend/src/types.generated.ts
	@echo "Generated: frontend/src/types.generated.ts"

clean:
	rm -rf backend/venv backend/dist backend/lambda.zip frontend/node_modules frontend/dist

help:
	@echo "AI Agent Commands"
	@echo ""
	@echo "  make install       Install all dependencies"
	@echo "  make env-setup     Create .env from template"
	@echo "  make dev           Run backend + frontend (hot reload)"
	@echo "  make dev-backend   Run backend only (hot reload)"
	@echo "  make dev-frontend  Run frontend only (hot reload)"
	@echo ""
	@echo "  make services-up   Start local AWS services (Docker)"
	@echo "  make services-down Stop local services"
	@echo "  make clean-data    Clear local S3/DynamoDB/OpenSearch"
	@echo ""
	@echo "  make build         Build for production"
	@echo "  make deploy        Build and deploy to AWS"
	@echo ""
	@echo "  make infra-setup   Create terraform.tfvars"
	@echo "  make infra-init    Initialize Terraform"
	@echo "  make infra-apply   Create AWS resources"
	@echo "  make infra-destroy Destroy AWS resources"
	@echo "  make infra-output  Show Terraform outputs"
	@echo ""
	@echo "  make generate-types  Generate TS types from Pydantic"
	@echo "  make clean           Remove build artifacts"

.DEFAULT_GOAL := help
