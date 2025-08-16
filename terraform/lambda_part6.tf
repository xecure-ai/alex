# Lambda Functions for Alex Agents - Part 6
# Simplified standalone version that can be deployed independently

# ========================================
# SQS Queue for Async Job Processing
# ========================================

resource "aws_sqs_queue" "analysis_jobs" {
  name                       = "alex-analysis-jobs"
  delay_seconds             = 0
  max_message_size          = 262144
  message_retention_seconds = 86400  # 1 day
  receive_wait_time_seconds = 10     # Long polling
  visibility_timeout_seconds = 900   # 15 minutes (Lambda timeout)
  
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.analysis_jobs_dlq.arn
    maxReceiveCount     = 3
  })
  
  tags = {
    Project = "alex"
    Part    = "6"
  }
}

resource "aws_sqs_queue" "analysis_jobs_dlq" {
  name = "alex-analysis-jobs-dlq"
  
  tags = {
    Project = "alex"
    Part    = "6"
  }
}

# ========================================
# IAM Role for Lambda Functions
# ========================================

resource "aws_iam_role" "lambda_agents_role" {
  name = "alex-lambda-agents-role"

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
  
  tags = {
    Project = "alex"
    Part    = "6"
  }
}

# Lambda basic execution policy
resource "aws_iam_role_policy_attachment" "lambda_agents_basic" {
  role       = aws_iam_role.lambda_agents_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for Lambda to access Bedrock and other services
resource "aws_iam_role_policy" "lambda_agents_policy" {
  name = "alex-lambda-agents-policy"
  role = aws_iam_role.lambda_agents_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "BedrockAccess"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      {
        Sid = "RDSDataAccess"
        Effect = "Allow"
        Action = [
          "rds-data:ExecuteStatement",
          "rds-data:BatchExecuteStatement",
          "rds-data:BeginTransaction",
          "rds-data:CommitTransaction",
          "rds-data:RollbackTransaction"
        ]
        Resource = "*"
      },
      {
        Sid = "SecretsAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:alex-*"
      },
      {
        Sid = "SQSAccess"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:SendMessage"
        ]
        Resource = [
          aws_sqs_queue.analysis_jobs.arn,
          aws_sqs_queue.analysis_jobs_dlq.arn
        ]
      },
      {
        Sid = "LambdaInvoke"
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:alex-*"
      },
      {
        Sid = "S3VectorsAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::alex-vectors-${data.aws_caller_identity.current.account_id}",
          "arn:aws:s3:::alex-vectors-${data.aws_caller_identity.current.account_id}/*"
        ]
      }
    ]
  })
}

# ========================================
# InstrumentTagger Lambda Function
# ========================================

resource "aws_lambda_function" "tagger" {
  filename         = "${path.module}/../backend/tagger/tagger_lambda.zip"
  function_name    = "alex-tagger"
  role            = aws_iam_role.lambda_agents_role.arn
  handler         = "lambda_handler.lambda_handler"
  runtime         = "python3.12"
  timeout         = 180
  memory_size     = 1024
  
  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      BEDROCK_MODEL_REGION = var.bedrock_model_region
      AURORA_CLUSTER_ARN = "arn:aws:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:cluster:alex-aurora-cluster"
      AURORA_SECRET_ARN = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:alex-aurora-data-api-credentials-aGIMlV"
      AURORA_DATABASE = "alex"
    }
  }
  
  # Only deploy if the zip file exists
  source_code_hash = fileexists("${path.module}/../backend/tagger/tagger_lambda.zip") ? filebase64sha256("${path.module}/../backend/tagger/tagger_lambda.zip") : null
  
  tags = {
    Project = "alex"
    Part    = "6"
    Agent   = "tagger"
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.lambda_agents_basic,
    aws_iam_role_policy.lambda_agents_policy
  ]
}

# ========================================
# S3 Bucket for Lambda Packages
# ========================================

resource "aws_s3_bucket" "lambda_packages" {
  bucket = "alex-lambda-packages-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Project = "alex"
    Part    = "6"
  }
}

# Upload Lambda packages to S3
resource "aws_s3_object" "planner_package" {
  bucket = aws_s3_bucket.lambda_packages.id
  key    = "lambda-packages/alex-planner.zip"
  source = "${path.module}/../backend/planner/planner_lambda.zip"
  etag   = fileexists("${path.module}/../backend/planner/planner_lambda.zip") ? filemd5("${path.module}/../backend/planner/planner_lambda.zip") : null
}

resource "aws_s3_object" "reporter_package" {
  bucket = aws_s3_bucket.lambda_packages.id
  key    = "lambda-packages/alex-reporter.zip"
  source = "${path.module}/../backend/reporter/reporter_lambda.zip"
  etag   = fileexists("${path.module}/../backend/reporter/reporter_lambda.zip") ? filemd5("${path.module}/../backend/reporter/reporter_lambda.zip") : null
}

resource "aws_s3_object" "charter_package" {
  bucket = aws_s3_bucket.lambda_packages.id
  key    = "lambda-packages/alex-charter.zip"
  source = "${path.module}/../backend/charter/charter_lambda.zip"
  etag   = fileexists("${path.module}/../backend/charter/charter_lambda.zip") ? filemd5("${path.module}/../backend/charter/charter_lambda.zip") : null
}

resource "aws_s3_object" "retirement_package" {
  bucket = aws_s3_bucket.lambda_packages.id
  key    = "lambda-packages/alex-retirement.zip"
  source = "${path.module}/../backend/retirement/retirement_lambda.zip"
  etag   = fileexists("${path.module}/../backend/retirement/retirement_lambda.zip") ? filemd5("${path.module}/../backend/retirement/retirement_lambda.zip") : null
}

# ========================================
# Planner (Orchestrator) Lambda Function
# ========================================

resource "aws_lambda_function" "planner" {
  function_name    = "alex-planner"
  role            = aws_iam_role.lambda_agents_role.arn
  handler         = "lambda_handler.lambda_handler"
  runtime         = "python3.12"
  timeout         = 900  # 15 minutes
  memory_size     = 3008
  
  s3_bucket = aws_s3_bucket.lambda_packages.id
  s3_key    = aws_s3_object.planner_package.key
  
  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      BEDROCK_MODEL_REGION = var.bedrock_model_region
      AURORA_CLUSTER_ARN = "arn:aws:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:cluster:alex-aurora-cluster"
      AURORA_SECRET_ARN = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:alex-aurora-data-api-credentials-aGIMlV"
      AURORA_DATABASE = "alex"
      VECTORS_BUCKET = "alex-vectors-${data.aws_caller_identity.current.account_id}"
      SAGEMAKER_ENDPOINT = "alex-embeddings"
      TAGGER_FUNCTION = aws_lambda_function.tagger.function_name
      REPORTER_FUNCTION = aws_lambda_function.reporter.function_name
      CHARTER_FUNCTION = aws_lambda_function.charter.function_name
      RETIREMENT_FUNCTION = aws_lambda_function.retirement.function_name
    }
  }
  
  # source_code_hash = aws_s3_object.planner_package.etag
  
  tags = {
    Project = "alex"
    Part    = "6"
    Agent   = "planner"
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.lambda_agents_basic,
    aws_iam_role_policy.lambda_agents_policy
  ]
}

# SQS trigger for Planner
resource "aws_lambda_event_source_mapping" "planner_sqs_trigger" {
  event_source_arn = aws_sqs_queue.analysis_jobs.arn
  function_name    = aws_lambda_function.planner.arn
  batch_size      = 1
}

# ========================================
# Reporter Lambda Function
# ========================================

resource "aws_lambda_function" "reporter" {
  function_name    = "alex-reporter"
  role            = aws_iam_role.lambda_agents_role.arn
  handler         = "lambda_handler.lambda_handler"
  runtime         = "python3.12"
  timeout         = 180
  memory_size     = 1024
  
  s3_bucket = aws_s3_bucket.lambda_packages.id
  s3_key    = aws_s3_object.reporter_package.key
  
  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      BEDROCK_MODEL_REGION = var.bedrock_model_region
      AURORA_CLUSTER_ARN = "arn:aws:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:cluster:alex-aurora-cluster"
      AURORA_SECRET_ARN = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:alex-aurora-data-api-credentials-aGIMlV"
      AURORA_DATABASE = "alex"
    }
  }
  
  # source_code_hash = aws_s3_object.reporter_package.etag
  
  tags = {
    Project = "alex"
    Part    = "6"
    Agent   = "reporter"
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.lambda_agents_basic,
    aws_iam_role_policy.lambda_agents_policy
  ]
}

# ========================================
# Charter Lambda Function
# ========================================

resource "aws_lambda_function" "charter" {
  function_name    = "alex-charter"
  role            = aws_iam_role.lambda_agents_role.arn
  handler         = "lambda_handler.lambda_handler"
  runtime         = "python3.12"
  timeout         = 180
  memory_size     = 1024
  
  s3_bucket = aws_s3_bucket.lambda_packages.id
  s3_key    = aws_s3_object.charter_package.key
  
  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      BEDROCK_MODEL_REGION = var.bedrock_model_region
      AURORA_CLUSTER_ARN = "arn:aws:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:cluster:alex-aurora-cluster"
      AURORA_SECRET_ARN = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:alex-aurora-data-api-credentials-aGIMlV"
      AURORA_DATABASE = "alex"
    }
  }
  
  # source_code_hash = aws_s3_object.charter_package.etag
  
  tags = {
    Project = "alex"
    Part    = "6"
    Agent   = "charter"
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.lambda_agents_basic,
    aws_iam_role_policy.lambda_agents_policy
  ]
}

# ========================================
# Retirement Lambda Function
# ========================================

resource "aws_lambda_function" "retirement" {
  function_name    = "alex-retirement"
  role            = aws_iam_role.lambda_agents_role.arn
  handler         = "lambda_handler.lambda_handler"
  runtime         = "python3.12"
  timeout         = 180
  memory_size     = 1024
  
  s3_bucket = aws_s3_bucket.lambda_packages.id
  s3_key    = aws_s3_object.retirement_package.key
  
  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      BEDROCK_MODEL_REGION = var.bedrock_model_region
      AURORA_CLUSTER_ARN = "arn:aws:rds:${var.aws_region}:${data.aws_caller_identity.current.account_id}:cluster:alex-aurora-cluster"
      AURORA_SECRET_ARN = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:alex-aurora-data-api-credentials-aGIMlV"
      AURORA_DATABASE = "alex"
    }
  }
  
  # source_code_hash = aws_s3_object.retirement_package.etag
  
  tags = {
    Project = "alex"
    Part    = "6"
    Agent   = "retirement"
  }
  
  depends_on = [
    aws_iam_role_policy_attachment.lambda_agents_basic,
    aws_iam_role_policy.lambda_agents_policy
  ]
}

# ========================================
# Outputs for Part 6
# ========================================

output "part6_sqs_queue_url" {
  value = aws_sqs_queue.analysis_jobs.url
  description = "URL of the SQS queue for job submission"
}

output "part6_lambda_functions" {
  value = {
    planner = aws_lambda_function.planner.function_name
    tagger = aws_lambda_function.tagger.function_name
    reporter = aws_lambda_function.reporter.function_name
    charter = aws_lambda_function.charter.function_name
    retirement = aws_lambda_function.retirement.function_name
  }
  description = "Names of all Lambda functions"
}

output "part6_lambda_role" {
  value = aws_iam_role.lambda_agents_role.arn
  description = "IAM role for Lambda agents"
}