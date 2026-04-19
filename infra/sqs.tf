# 変換ジョブキュー（デッドレターキュー付き）
resource "aws_sqs_queue" "conversion_dlq" {
  name                      = "${var.app_name}-conversion-dlq"
  message_retention_seconds = 86400 # 1日
  tags                      = local.common_tags
}

resource "aws_sqs_queue" "conversion" {
  name                       = "${var.app_name}-conversion"
  visibility_timeout_seconds = var.worker_lambda_timeout + 30 # Lambdaタイムアウトより少し長く
  message_retention_seconds  = 3600                           # 1時間
  receive_wait_time_seconds  = 20                             # ロングポーリング

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.conversion_dlq.arn
    maxReceiveCount     = 3 # 3回失敗したらDLQへ
  })

  tags = local.common_tags
}
