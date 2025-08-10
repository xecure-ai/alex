variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "deployment_package_path" {
  description = "Path to the Lambda deployment package"
  type        = string
}

variable "vector_bucket_name" {
  description = "Name of the S3 Vector bucket"
  type        = string
}

variable "vector_bucket_arn" {
  description = "ARN of the S3 Vector bucket"
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