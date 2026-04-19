variable "aws_region" {
  description = "AWSリージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "app_name" {
  description = "アプリケーション名（リソース名のプレフィックス）"
  type        = string
  default     = "chroma-sync"
}

variable "environment" {
  description = "環境名（production / staging）"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "カスタムドメイン名（例: chroma-sync.example.com）。空文字の場合はCloudFrontドメインを使用"
  type        = string
  default     = ""
}

variable "api_lambda_image_uri" {
  description = "API Lambda用のECRイメージURI"
  type        = string
  default     = ""
}

variable "worker_lambda_image_uri" {
  description = "Worker Lambda用のECRイメージURI"
  type        = string
  default     = ""
}

variable "api_lambda_memory" {
  description = "API Lambda のメモリ（MB）"
  type        = number
  default     = 512
}

variable "worker_lambda_memory" {
  description = "Worker Lambda のメモリ（MB）。大きなファイルの変換に必要"
  type        = number
  default     = 3008
}

variable "worker_lambda_timeout" {
  description = "Worker Lambda のタイムアウト（秒）"
  type        = number
  default     = 300
}

variable "worker_lambda_ephemeral_storage" {
  description = "Worker Lambda の /tmp ストレージ（MB）。大きなAI/PSDファイルに必要"
  type        = number
  default     = 2048
}

variable "cors_origins" {
  description = "CORSで許可するオリジン（カンマ区切り）"
  type        = string
  default     = "*"
}

variable "max_upload_size_mb" {
  description = "最大アップロードサイズ（MB）"
  type        = number
  default     = 100
}
