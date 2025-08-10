output "sagemaker_endpoint_name" {
  description = "Name of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.embedding_endpoint.name
}

output "sagemaker_endpoint_arn" {
  description = "ARN of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.embedding_endpoint.arn
}

output "sagemaker_role_arn" {
  description = "IAM role ARN for SageMaker"
  value       = aws_iam_role.sagemaker_role.arn
}

# S3 Vectors outputs
output "vector_bucket_name" {
  description = "S3 Vector bucket name"
  value       = module.s3_vectors.bucket_name
}

# Lambda outputs
output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = module.lambda.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = module.lambda.function_arn
}

# API Gateway outputs
output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = module.api_gateway.api_endpoint
}

output "api_key_value" {
  description = "API Key value (sensitive - use terraform output -raw api_key_value to see it)"
  value       = module.api_gateway.api_key_value
  sensitive   = true
}

# App Runner outputs
output "researcher_service_url" {
  description = "URL of the researcher App Runner service"
  value       = "https://${module.app_runner.service_url}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for researcher Docker images"
  value       = module.app_runner.ecr_repository_url
}