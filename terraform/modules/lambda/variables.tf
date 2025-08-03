variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "alex-ingest"
}

variable "deployment_package_path" {
  description = "Path to the Lambda deployment package (zip file)"
  type        = string
}

variable "opensearch_endpoint" {
  description = "OpenSearch Serverless collection endpoint"
  type        = string
}

variable "opensearch_collection_arn" {
  description = "ARN of the OpenSearch Serverless collection"
  type        = string
}

variable "sagemaker_endpoint_name" {
  description = "Name of the SageMaker endpoint"
  type        = string
}

variable "sagemaker_endpoint_arn" {
  description = "ARN of the SageMaker endpoint"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}