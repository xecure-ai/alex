output "collection_endpoint" {
  description = "OpenSearch Serverless collection endpoint"
  value       = aws_opensearchserverless_collection.alex.collection_endpoint
}

output "collection_id" {
  description = "OpenSearch Serverless collection ID"
  value       = aws_opensearchserverless_collection.alex.id
}

output "collection_arn" {
  description = "OpenSearch Serverless collection ARN"
  value       = aws_opensearchserverless_collection.alex.arn
}