
output "sagemaker_endpoint_name" {
  description = "Name of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.embedding_endpoint.name
}

output "sagemaker_endpoint_arn" {
  description = "ARN of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.embedding_endpoint.arn
}

output "setup_instructions" {
  description = "Instructions for setting up environment variables"
  value = <<-EOT
    
    ✅ SageMaker endpoint deployed successfully!
    
    Add the following to your .env file:
    SAGEMAKER_ENDPOINT=${aws_sagemaker_endpoint.embedding_endpoint.name}
    
    Test the endpoint:
    aws sagemaker-runtime invoke-endpoint \
      --endpoint-name ${aws_sagemaker_endpoint.embedding_endpoint.name} \
      --content-type application/json \
      --body '{"inputs": "Hello world"}' \
      response.json
  EOT
}