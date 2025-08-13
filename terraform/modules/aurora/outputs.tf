output "cluster_arn" {
  description = "ARN of the Aurora cluster for Data API access"
  value       = aws_rds_cluster.alex_db.arn
}

output "secret_arn" {
  description = "ARN of the secret containing database credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "database_name" {
  description = "Name of the database"
  value       = var.database_name
}

output "cluster_endpoint" {
  description = "Cluster endpoint (for reference, not used with Data API)"
  value       = aws_rds_cluster.alex_db.endpoint
}

output "cluster_identifier" {
  description = "Cluster identifier"
  value       = aws_rds_cluster.alex_db.cluster_identifier
}