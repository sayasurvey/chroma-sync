terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # bootstrap.sh実行後にS3バックエンドが有効になる
  # terraform init時に -backend-config で bucket名を渡す
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

# CloudFrontはus-east-1のリソース（ACM証明書）を参照するため別プロバイダーが必要
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
