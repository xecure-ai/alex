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