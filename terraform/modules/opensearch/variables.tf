variable "collection_name" {
  description = "Name of the OpenSearch Serverless collection"
  type        = string
  default     = "alex-portfolio"
}

variable "lambda_role_arn" {
  description = "ARN of the Lambda function's IAM role"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}