#!/bin/bash
set -e

echo "🔧 Initializing LocalStack resources..."

# Create S3 bucket for documents
awslocal s3 mb s3://ai-agent-documents-local || true

# Enable CORS on the bucket (for presigned URL uploads from browser)
awslocal s3api put-bucket-cors --bucket ai-agent-documents-local --cors-configuration '{
  "CORSRules": [{
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": ["ETag", "Content-Length", "Content-Type"],
    "MaxAgeSeconds": 3600
  }]
}'

# Create DynamoDB table for jobs
awslocal dynamodb create-table \
  --table-name ai-agent-jobs \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  2>/dev/null || true

echo "✅ LocalStack initialized!"
echo "   S3 Bucket: ai-agent-documents-local"
echo "   DynamoDB Table: ai-agent-jobs"
