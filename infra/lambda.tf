# API Lambda（FastAPI/Mangum）
resource "aws_lambda_function" "api" {
  function_name = "${var.app_name}-api"
  role          = aws_iam_role.api_lambda.arn
  package_type  = "Image"
  image_uri     = var.api_lambda_image_uri

  memory_size = var.api_lambda_memory
  timeout     = 30

  image_config {
    command = ["lambda_handler.handler"]
  }

  environment {
    variables = {
      S3_BUCKET        = aws_s3_bucket.uploads.id
      DYNAMODB_TABLE   = aws_dynamodb_table.jobs.name
      SQS_QUEUE_URL    = aws_sqs_queue.conversion.url
      AWS_DEFAULT_REGION = var.aws_region
      CORS_ORIGINS     = var.cors_origins
      MAX_UPLOAD_SIZE_MB = tostring(var.max_upload_size_mb)
    }
  }

  tags = local.common_tags
}

# Worker Lambda（ImageMagick変換処理）
resource "aws_lambda_function" "worker" {
  function_name = "${var.app_name}-worker"
  role          = aws_iam_role.worker_lambda.arn
  package_type  = "Image"
  image_uri     = var.worker_lambda_image_uri

  memory_size = var.worker_lambda_memory
  timeout     = var.worker_lambda_timeout

  ephemeral_storage {
    size = var.worker_lambda_ephemeral_storage
  }

  image_config {
    command = ["worker_handler.handler"]
  }

  environment {
    variables = {
      S3_BUCKET        = aws_s3_bucket.uploads.id
      DYNAMODB_TABLE   = aws_dynamodb_table.jobs.name
      SQS_QUEUE_URL    = aws_sqs_queue.conversion.url
      AWS_DEFAULT_REGION = var.aws_region
      MAX_UPLOAD_SIZE_MB = tostring(var.max_upload_size_mb)
    }
  }

  tags = local.common_tags
}

# SQSトリガー（Worker LambdaをSQSメッセージで起動）
resource "aws_lambda_event_source_mapping" "worker_sqs" {
  event_source_arn                   = aws_sqs_queue.conversion.arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = 1 # 1ジョブずつ処理
  maximum_batching_window_in_seconds = 0

  function_response_types = ["ReportBatchItemFailures"]
}

# API Lambda用のCloudWatchロググループ
resource "aws_cloudwatch_log_group" "api_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 7
  tags              = local.common_tags
}

# Worker Lambda用のCloudWatchロググループ
resource "aws_cloudwatch_log_group" "worker_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.worker.function_name}"
  retention_in_days = 7
  tags              = local.common_tags
}
