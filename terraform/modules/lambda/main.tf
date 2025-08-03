# IAM role for Lambda function
resource "aws_iam_role" "lambda" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda.name
}

# Policy for accessing OpenSearch Serverless
resource "aws_iam_role_policy" "opensearch_access" {
  name = "${var.function_name}-opensearch-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = var.opensearch_collection_arn
      }
    ]
  })
}

# Policy for invoking SageMaker endpoint
resource "aws_iam_role_policy" "sagemaker_invoke" {
  name = "${var.function_name}-sagemaker-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sagemaker:InvokeEndpoint"
        ]
        Resource = var.sagemaker_endpoint_arn
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "ingest" {
  filename         = var.deployment_package_path
  function_name    = var.function_name
  role            = aws_iam_role.lambda.arn
  handler         = "ingest.lambda_handler"
  source_code_hash = filebase64sha256(var.deployment_package_path)
  runtime         = "python3.12"
  timeout         = 30
  memory_size     = 512

  environment {
    variables = {
      OPENSEARCH_ENDPOINT = var.opensearch_endpoint
      SAGEMAKER_ENDPOINT  = var.sagemaker_endpoint_name
    }
  }

  tags = var.tags
}