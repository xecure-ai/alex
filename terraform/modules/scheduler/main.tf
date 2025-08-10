variable "app_runner_url" {
  description = "The App Runner service URL"
  type        = string
}

variable "enabled" {
  description = "Whether to enable the automated scheduler"
  type        = bool
  default     = false
}

# Create a zip file for the Lambda function
data "archive_file" "lambda_zip" {
  count       = var.enabled ? 1 : 0
  type        = "zip"
  source_file = "${path.module}/lambda_function.py"
  output_path = "${path.module}/lambda_function.zip"
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  count = var.enabled ? 1 : 0
  name  = "alex-scheduler-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  count      = var.enabled ? 1 : 0
  role       = aws_iam_role.lambda_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda function to call the App Runner endpoint
resource "aws_lambda_function" "scheduler" {
  count         = var.enabled ? 1 : 0
  filename      = data.archive_file.lambda_zip[0].output_path
  function_name = "alex-research-scheduler"
  role          = aws_iam_role.lambda_role[0].arn
  handler       = "lambda_function.handler"
  runtime       = "python3.11"
  timeout       = 150  # 2.5 minutes timeout (research takes 30-60s, with buffer)
  
  source_code_hash = data.archive_file.lambda_zip[0].output_base64sha256

  environment {
    variables = {
      APP_RUNNER_URL = var.app_runner_url
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_logs
  ]
}

# EventBridge rule to trigger every 2 hours
resource "aws_cloudwatch_event_rule" "schedule" {
  count               = var.enabled ? 1 : 0
  name                = "alex-research-schedule"
  description         = "Trigger research every 2 hours"
  schedule_expression = "rate(2 hours)"
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  count         = var.enabled ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule[0].arn
}

# Target connecting the EventBridge rule to Lambda
resource "aws_cloudwatch_event_target" "lambda" {
  count     = var.enabled ? 1 : 0
  rule      = aws_cloudwatch_event_rule.schedule[0].name
  target_id = "LambdaTarget"
  arn       = aws_lambda_function.scheduler[0].arn
}

output "schedule_status" {
  value = var.enabled ? "ENABLED - Running every 2 hours" : "DISABLED - Not running"
}

output "lambda_function_name" {
  value = var.enabled ? aws_lambda_function.scheduler[0].function_name : ""
}