provider "aws" {
  region = var.region
}

# Define a zip archive file from source directory and save to output directory
data "archive_file" "lambda_function_zip" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = var.output_dir
}

# Define IAM role for Lambda execution with policy attachment
resource "aws_iam_role" "lambda_execution_role" {
  name               = "lambda_execution_role"
  assume_role_policy = var.add_policy
}

# Attach policy for Lambda execution to IAM role
resource "aws_iam_role_policy_attachment" "lambda_logs_policy" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_execution_role.name
}

# Define Lambda function
resource "aws_lambda_function" "my_lambda_function" {
  filename         = data.archive_file.lambda_function_zip.output_path
  function_name    = "my-lambda-function"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  memory_size      = 128
  timeout          = 60
  source_code_hash = data.archive_file.lambda_function_zip.output_base64sha256
}

# Create API Gateway
resource "aws_api_gateway_rest_api" "my_api_gateway" {
  name = "my-api-gateway"
}

# Create a resource
resource "aws_api_gateway_resource" "my_resource" {
  rest_api_id = aws_api_gateway_rest_api.my_api_gateway.id
  parent_id   = aws_api_gateway_rest_api.my_api_gateway.root_resource_id
  path_part   = "my-resource"
}

# Create a method
resource "aws_api_gateway_method" "my_method" {
  rest_api_id   = aws_api_gateway_rest_api.my_api_gateway.id
  resource_id   = aws_api_gateway_resource.my_resource.id
  http_method   = "ANY"
  authorization = "NONE"
}

# Create an integration
resource "aws_api_gateway_integration" "my_lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.my_api_gateway.id
  resource_id = aws_api_gateway_resource.my_resource.id
  http_method = aws_api_gateway_method.my_method.http_method

  integration_http_method = "ANY"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.my_lambda_function.invoke_arn
}

# Create Lambda permission for API Gateway to invoke Lambda
resource "aws_lambda_permission" "api_gateway_permission" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.my_lambda_function.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_api_gateway_rest_api.my_api_gateway.execution_arn}/*/*"
}

# Deploy API
resource "aws_api_gateway_deployment" "my_deployment" {
  depends_on  = [aws_api_gateway_integration.my_lambda_integration]
  rest_api_id = aws_api_gateway_rest_api.my_api_gateway.id
}

resource "aws_api_gateway_stage" "my_stage" {
  deployment_id = aws_api_gateway_deployment.my_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.my_api_gateway.id
  stage_name    = "prod"
}

# Export the URL of the API Gateway deployment
output "api_gateway_url" {
  value = "https://${aws_api_gateway_rest_api.my_api_gateway.id}.execute-api.${var.region}.amazonaws.com/${aws_api_gateway_stage.my_stage.stage_name}/${aws_api_gateway_resource.my_resource.path_part}"
}
