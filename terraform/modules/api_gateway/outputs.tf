output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.api_with_key.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_api_gateway_stage.api.stage_name}"
}

output "api_key_id" {
  description = "API Key ID"
  value       = aws_api_gateway_api_key.api_key.id
}

output "api_key_value" {
  description = "API Key value (sensitive)"
  value       = aws_api_gateway_api_key.api_key.value
  sensitive   = true
}

# Data source for current region
data "aws_region" "current" {}