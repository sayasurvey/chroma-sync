output "cloudfront_domain" {
  description = "CloudFrontドメイン名（フロントエンドURL）"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "api_gateway_url" {
  description = "API Gateway エンドポイントURL"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "frontend_bucket" {
  description = "フロントエンド静的ファイルのS3バケット名"
  value       = aws_s3_bucket.frontend.id
}

output "uploads_bucket" {
  description = "アップロードファイルのS3バケット名"
  value       = aws_s3_bucket.uploads.id
}

output "dynamodb_table" {
  description = "DynamoDBテーブル名"
  value       = aws_dynamodb_table.jobs.name
}

output "sqs_queue_url" {
  description = "SQSキューURL"
  value       = aws_sqs_queue.conversion.url
}

output "ecr_api_repository_url" {
  description = "API Lambda用ECRリポジトリURL"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_worker_repository_url" {
  description = "Worker Lambda用ECRリポジトリURL"
  value       = aws_ecr_repository.worker.repository_url
}

output "cloudfront_distribution_id" {
  description = "CloudFrontディストリビューションID（キャッシュ無効化用）"
  value       = aws_cloudfront_distribution.main.id
}

output "custom_domain_url" {
  description = "カスタムドメインURL（設定した場合）"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "（カスタムドメインなし）"
}
