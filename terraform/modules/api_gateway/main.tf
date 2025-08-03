# API Gateway HTTP API
resource "aws_apigatewayv2_api" "api" {
  name          = var.api_name
  protocol_type = "HTTP"
  description   = "API Gateway for Alex portfolio ingest"

  tags = var.tags
}

# API Gateway stage
resource "aws_apigatewayv2_stage" "api" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = var.stage_name
  auto_deploy = true

  tags = var.tags
}

# Lambda integration
resource "aws_apigatewayv2_integration" "lambda" {
  api_id = aws_apigatewayv2_api.api.id

  integration_type       = "AWS_PROXY"
  integration_uri        = var.lambda_invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# Route for POST /ingest
resource "aws_apigatewayv2_route" "ingest" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /ingest"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"

  authorization_type = "AWS_IAM"
}

# Lambda permission for API Gateway to invoke
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

# API Key for authentication (using AWS API Gateway v1 for API key support)
resource "aws_api_gateway_rest_api" "api_with_key" {
  name        = "${var.api_name}-with-key"
  description = "REST API with API Key authentication for Alex"
}

resource "aws_api_gateway_resource" "ingest" {
  rest_api_id = aws_api_gateway_rest_api.api_with_key.id
  parent_id   = aws_api_gateway_rest_api.api_with_key.root_resource_id
  path_part   = "ingest"
}

resource "aws_api_gateway_method" "ingest" {
  rest_api_id      = aws_api_gateway_rest_api.api_with_key.id
  resource_id      = aws_api_gateway_resource.ingest.id
  http_method      = "POST"
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id = aws_api_gateway_rest_api.api_with_key.id
  resource_id = aws_api_gateway_resource.ingest.id
  http_method = aws_api_gateway_method.ingest.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = var.lambda_invoke_arn
}

resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api_with_key.id

  depends_on = [
    aws_api_gateway_method.ingest,
    aws_api_gateway_integration.lambda
  ]
  
  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "api" {
  deployment_id = aws_api_gateway_deployment.api.id
  rest_api_id   = aws_api_gateway_rest_api.api_with_key.id
  stage_name    = var.stage_name
}

# API Key
resource "aws_api_gateway_api_key" "api_key" {
  name        = "${var.api_name}-key"
  description = "API key for Alex portfolio ingest"
}

# Usage plan
resource "aws_api_gateway_usage_plan" "plan" {
  name        = "${var.api_name}-usage-plan"
  description = "Usage plan for Alex API"

  api_stages {
    api_id = aws_api_gateway_rest_api.api_with_key.id
    stage  = aws_api_gateway_stage.api.stage_name
  }

  quota_settings {
    limit  = 10000
    period = "MONTH"
  }

  throttle_settings {
    rate_limit  = 100
    burst_limit = 200
  }
}

# Usage plan key
resource "aws_api_gateway_usage_plan_key" "plan_key" {
  key_id        = aws_api_gateway_api_key.api_key.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.plan.id
}

# Lambda permission for REST API Gateway to invoke
resource "aws_lambda_permission" "rest_api_gateway" {
  statement_id  = "AllowRESTAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api_with_key.execution_arn}/*/*"
}