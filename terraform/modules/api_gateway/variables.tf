variable "api_name" {
  description = "Name of the API Gateway"
  type        = string
  default     = "alex-api"
}

variable "stage_name" {
  description = "Name of the API Gateway stage"
  type        = string
  default     = "prod"
}

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "lambda_invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}