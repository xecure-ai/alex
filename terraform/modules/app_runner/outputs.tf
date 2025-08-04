output "service_url" {
  description = "URL of the App Runner service"
  value       = aws_apprunner_service.researcher.service_url
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.researcher.repository_url
}

output "service_arn" {
  description = "ARN of the App Runner service"
  value       = aws_apprunner_service.researcher.arn
}