#!/usr/bin/env bash
# 初回のみ実行するブートストラップスクリプト
# GitHub Actions用のOIDCプロバイダー・IAMロール・Terraform state用S3バケットを作成する
set -euo pipefail

GITHUB_ORG="sayasurvey"
GITHUB_REPO="chroma-sync"
APP_NAME="chroma-sync"
AWS_REGION="ap-northeast-1"

echo "=== AWSアカウント情報を取得中 ==="
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "アカウントID: $ACCOUNT_ID"
echo "リージョン: $AWS_REGION"

TF_STATE_BUCKET="${APP_NAME}-tfstate-${ACCOUNT_ID}"
ROLE_NAME="${APP_NAME}-github-actions-role"
OIDC_PROVIDER_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

# ──── 1. Terraform state用S3バケット ────
echo ""
echo "=== Terraform state用S3バケットを作成中: $TF_STATE_BUCKET ==="
if aws s3api head-bucket --bucket "$TF_STATE_BUCKET" 2>/dev/null; then
  echo "バケットは既に存在します（スキップ）"
else
  aws s3api create-bucket \
    --bucket "$TF_STATE_BUCKET" \
    --region "$AWS_REGION" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION"
  echo "バケット作成完了"
fi

aws s3api put-bucket-versioning \
  --bucket "$TF_STATE_BUCKET" \
  --versioning-configuration Status=Enabled

aws s3api put-public-access-block \
  --bucket "$TF_STATE_BUCKET" \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
echo "バージョニング・パブリックアクセスブロック設定完了"

# ──── 2. GitHub Actions用OIDCプロバイダー ────
echo ""
echo "=== GitHub Actions用OIDCプロバイダーを確認中 ==="
if aws iam get-open-id-connect-provider \
    --open-id-connect-provider-arn "$OIDC_PROVIDER_ARN" 2>/dev/null; then
  echo "OIDCプロバイダーは既に存在します（スキップ）"
else
  aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list \
      "6938fd4d98bab03faadb97b34396831e3780aea1" \
      "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
  echo "OIDCプロバイダー作成完了"
fi

# ──── 3. GitHub Actions用IAMロール ────
echo ""
echo "=== GitHub Actions用IAMロールを作成中: $ROLE_NAME ==="

TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "${OIDC_PROVIDER_ARN}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF
)

if aws iam get-role --role-name "$ROLE_NAME" 2>/dev/null; then
  echo "IAMロールは既に存在します（信頼ポリシーを更新）"
  aws iam update-assume-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-document "$TRUST_POLICY"
else
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "$TRUST_POLICY" \
    --description "GitHub Actions OIDC role for ${GITHUB_REPO}"
  echo "IAMロール作成完了"
fi

# 必要なマネージドポリシーをアタッチ
POLICIES=(
  "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess"
  "arn:aws:iam::aws:policy/AmazonS3FullAccess"
  "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
  "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
  "arn:aws:iam::aws:policy/AmazonAPIGatewayAdministrator"
  "arn:aws:iam::aws:policy/CloudFrontFullAccess"
  "arn:aws:iam::aws:policy/AmazonSQSFullAccess"
  "arn:aws:iam::aws:policy/IAMFullAccess"
  "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
)

echo "ポリシーをアタッチ中..."
for policy_arn in "${POLICIES[@]}"; do
  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "$policy_arn" 2>/dev/null || true
  echo "  ✓ $policy_arn"
done

# Terraform stateバケットへのインラインポリシー
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "terraform-state-access" \
  --policy-document "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::${TF_STATE_BUCKET}",
        "arn:aws:s3:::${TF_STATE_BUCKET}/*"
      ]
    }
  ]
}
EOF
)"

ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)

# 結果を .env.deploy に保存（コミット不可）
cat > .env.deploy <<ENVEOF
AWS_ROLE_ARN=${ROLE_ARN}
TF_STATE_BUCKET=${TF_STATE_BUCKET}
AWS_ACCOUNT_ID=${ACCOUNT_ID}
ENVEOF

echo ""
echo "=========================================="
echo "ブートストラップ完了！"
echo "=========================================="
echo ""
echo "次のステップ:"
echo ""
echo "1. GitHubリポジトリにSecretを追加してください:"
echo "   https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/settings/secrets/actions"
echo ""
echo "   AWS_ROLE_ARN = ${ROLE_ARN}"
echo ""
echo "2. mainブランチにマージするとデプロイが自動実行されます"
echo ""
echo "（上記の情報は .env.deploy にも保存されています）"
