variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "sagemaker_image_uri" {
  description = "Docker image URI for SageMaker inference"
  type        = string
  # Using HuggingFace inference container optimized for transformers
  default = "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:2.1.0-transformers4.37.0-cpu-py310-ubuntu22.04"
}

variable "embedding_model_name" {
  description = "Name of the Hugging Face model to use for embeddings"
  type        = string
  default     = "sentence-transformers/all-MiniLM-L6-v2"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "alex"
}

variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
  default     = "prod"
}

variable "openai_api_key" {
  description = "OpenAI API key for the researcher service"
  type        = string
  sensitive   = true
  default     = "placeholder-will-be-set-in-guide-4"
}

variable "scheduler_enabled" {
  description = "Enable automated research every 2 hours"
  type        = bool
  default     = false
}