# AWS App Runner for Researcher Service

# IAM role for App Runner (Access Role - for ECR)
resource "aws_iam_role" "app_runner_role" {
  name = "${var.service_name}-app-runner-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "tasks.apprunner.amazonaws.com",
            "build.apprunner.amazonaws.com"
          ]
        }
      }
    ]
  })
}

# IAM role for App Runner Instance (Task Role - for running container)
resource "aws_iam_role" "app_runner_instance_role" {
  name = "${var.service_name}-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

# Attach ECR read policy for image pulling
resource "aws_iam_role_policy_attachment" "app_runner_ecr_access" {
  role       = aws_iam_role.app_runner_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Add Bedrock access policy to instance role (for running container)
resource "aws_iam_role_policy" "app_runner_bedrock_access" {
  name = "${var.service_name}-bedrock-access"
  role = aws_iam_role.app_runner_instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECR Repository for Docker images
resource "aws_ecr_repository" "researcher" {
  name                 = var.service_name
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = false
  }
  
  tags = var.tags
}

# App Runner Service
resource "aws_apprunner_service" "researcher" {
  service_name = var.service_name
  
  source_configuration {
    image_repository {
      image_configuration {
        port = "8000"
        runtime_environment_variables = var.environment_variables
      }
      image_identifier      = "${aws_ecr_repository.researcher.repository_url}:latest"
      image_repository_type = "ECR"
    }
    
    authentication_configuration {
      access_role_arn = aws_iam_role.app_runner_role.arn
    }
    
    auto_deployments_enabled = false
  }
  
  instance_configuration {
    cpu    = var.cpu
    memory = var.memory
    instance_role_arn = aws_iam_role.app_runner_instance_role.arn
  }
  
  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 2
  }
  
  tags = var.tags
}