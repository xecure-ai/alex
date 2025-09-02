terraform {
  required_version = ">= 1.5"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Using local backend - state will be stored in terraform.tfstate in this directory
  # This is automatically gitignored for security
}

provider "aws" {
  region = var.aws_region
}

# Data source for current caller identity
data "aws_caller_identity" "current" {}

# Determine the correct HuggingFace container image based on region
locals {
  region_to_account = {
    "us-east-1"      = "763104351884"
    "us-east-2"      = "763104351884"
    "us-west-1"      = "763104351884"
    "us-west-2"      = "763104351884"
    "eu-west-1"      = "763104351884"
    "eu-west-2"      = "763104351884"
    "eu-west-3"      = "763104351884"
    "eu-central-1"   = "763104351884"
    "eu-north-1"     = "763104351884"
    "ap-northeast-1" = "763104351884"
    "ap-northeast-2" = "763104351884"
    "ap-south-1"     = "763104351884"
    "ap-southeast-1" = "763104351884"
    "ap-southeast-2" = "763104351884"
  }
  
  ecr_account = lookup(local.region_to_account, var.aws_region, "763104351884")
  default_image_uri = "${local.ecr_account}.dkr.ecr.${var.aws_region}.amazonaws.com/huggingface-pytorch-inference:2.0.0-transformers4.28.1-cpu-py310-ubuntu20.04"
}

# IAM role for SageMaker
resource "aws_iam_role" "sagemaker_role" {
  name = "alex-sagemaker-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Project = "alex"
    Part    = "2"
  }
}

resource "aws_iam_role_policy_attachment" "sagemaker_full_access" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

# SageMaker Model
resource "aws_sagemaker_model" "embedding_model" {
  name               = "alex-embedding-model"
  execution_role_arn = aws_iam_role.sagemaker_role.arn

  primary_container {
    image = local.default_image_uri
    environment = {
      HF_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
      HF_TASK     = "feature-extraction"
    }
  }

  depends_on = [aws_iam_role_policy_attachment.sagemaker_full_access]
  
  tags = {
    Project = "alex"
    Part    = "2"
  }
}

# Serverless Inference Config
resource "aws_sagemaker_endpoint_configuration" "serverless_config" {
  name = "alex-embedding-serverless-config"

  production_variants {
    model_name = aws_sagemaker_model.embedding_model.name
    
    serverless_config {
      memory_size_in_mb = 3072
      max_concurrency   = 10
    }
  }
  
  tags = {
    Project = "alex"
    Part    = "2"
  }
}

# SageMaker Endpoint
resource "aws_sagemaker_endpoint" "embedding_endpoint" {
  name                 = "alex-embedding-endpoint"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.serverless_config.name
  
  depends_on = [
    aws_iam_role_policy_attachment.sagemaker_full_access
  ]
  
  tags = {
    Project = "alex"
    Part    = "2"
  }
}