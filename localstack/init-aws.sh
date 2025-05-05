#!/bin/bash
# localstack/init-aws.sh - Initialize AWS resources in LocalStack

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
while ! curl -s http://localhost:4566/_localstack/health >/dev/null; do
  sleep 1
done

echo "LocalStack is ready!"

# Create S3 bucket
echo "Creating S3 bucket: audio-files"
awslocal --endpoint-url=http://localhost:4566 s3 mb s3://audio-files

# Create SQS queue
echo "Creating SQS queue: audio-processing-queue"
awslocal --endpoint-url=http://localhost:4566 sqs create-queue --queue-name audio-processing-queue

# Create DynamoDB tables
echo "Creating DynamoDB table: AudioTranscriptions"
awslocal --endpoint-url=http://localhost:4566 dynamodb create-table \
    --table-name AudioTranscriptions \
    --attribute-definitions AttributeName=job_id,AttributeType=S \
    --key-schema AttributeName=job_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST

echo "Creating DynamoDB table: DiaryNotes"
awslocal --endpoint-url=http://localhost:4566 dynamodb create-table \
    --table-name DiaryNotes \
    --attribute-definitions AttributeName=job_id,AttributeType=S \
    --key-schema AttributeName=job_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST

echo "AWS resources initialized successfully!"