#!/bin/bash
# Deploy researcher service to AWS App Runner

set -e

echo "Alex Researcher Service - Docker Deployment"
echo "==========================================="

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REPOSITORY="alex-researcher"

echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo ""

# Get ECR repository URL from Terraform
echo "Getting ECR repository URL..."
cd ../../terraform
ECR_URL=$(terraform output -raw ecr_repository_url 2>/dev/null || echo "")
cd ../backend/researcher

if [ -z "$ECR_URL" ]; then
    echo "Error: ECR repository not found. Run 'terraform apply' first."
    exit 1
fi

echo "ECR Repository: $ECR_URL"
echo ""

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL

# Build Docker image (specify platform for App Runner compatibility)
echo "Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t $ECR_REPOSITORY:latest .

# Tag for ECR
echo "Tagging image for ECR..."
docker tag $ECR_REPOSITORY:latest $ECR_URL:latest

# Push to ECR
echo "Pushing image to ECR..."
docker push $ECR_URL:latest

echo ""
echo "✅ Docker image pushed successfully!"
echo ""
echo "Now update the App Runner service:"
echo "  1. Go to AWS Console > App Runner"
echo "  2. Select 'alex-researcher' service"
echo "  3. Click 'Deploy' to pull the latest image"
echo ""
echo "Or use AWS CLI:"
echo "  aws apprunner start-deployment --service-arn <service-arn>"