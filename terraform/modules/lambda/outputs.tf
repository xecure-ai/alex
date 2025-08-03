output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.ingest.arn
}

output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.ingest.function_name
}

output "role_arn" {
  description = "ARN of the Lambda function's IAM role"
  value       = aws_iam_role.lambda.arn
}

output "invoke_arn" {
  description = "Invoke ARN for API Gateway integration"
  value       = aws_lambda_function.ingest.invoke_arn
}