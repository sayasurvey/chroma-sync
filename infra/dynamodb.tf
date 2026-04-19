# 変換ジョブ状態管理テーブル
resource "aws_dynamodb_table" "jobs" {
  name         = "${var.app_name}-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "job_id"

  attribute {
    name = "job_id"
    type = "S"
  }

  # TTL属性（24時間後に自動削除）
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = local.common_tags
}
