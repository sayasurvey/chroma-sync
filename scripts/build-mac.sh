#!/usr/bin/env bash
# macOS向けのChromaSync デスクトップアプリビルドスクリプト
# 前提: Homebrew, Node.js 20 がインストール済みであること（Python 3.11 は未インストールでも自動取得）

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== ChromaSync macOS ビルド開始 ==="

# -----------------------------------------------------------------------
# [1/5] 依存ツールの確認
# -----------------------------------------------------------------------
echo "[1/5] 依存ツールの確認..."
command -v brew >/dev/null || { echo "Error: Homebrewが必要です (https://brew.sh)"; exit 1; }
command -v node >/dev/null || { echo "Error: Node.js 20が必要です"; exit 1; }

# -----------------------------------------------------------------------
# [2/5] Python 3.11 の確認・インストール
# -----------------------------------------------------------------------
echo "[2/5] Python 3.11 の確認..."

# 優先順位: brew python3.11 > pyenv python3.11 > system
PYTHON311=""
for candidate in \
  "$(brew --prefix python@3.11 2>/dev/null)/bin/python3.11" \
  "/opt/homebrew/bin/python3.11" \
  "/usr/local/bin/python3.11" \
  "$(pyenv root 2>/dev/null)/shims/python3.11"; do
  if [ -x "$candidate" ]; then
    PYTHON311="$candidate"
    break
  fi
done

# pyenv shim経由でも確認
if [ -z "$PYTHON311" ] && command -v pyenv &>/dev/null; then
  if pyenv versions --bare 2>/dev/null | grep -q '^3\.11'; then
    PYTHON311="$(pyenv root)/shims/python3.11"
  fi
fi

if [ -z "$PYTHON311" ]; then
  echo "Python 3.11が見つかりません。Homebrewでインストールします..."
  brew install python@3.11
  PYTHON311="$(brew --prefix python@3.11)/bin/python3.11"
fi

echo "使用するPython: $PYTHON311 ($("$PYTHON311" --version))"

# -----------------------------------------------------------------------
# [3/5] ImageMagick の確認・インストール
# -----------------------------------------------------------------------
echo "[3/5] ImageMagickのインストール確認..."
if ! brew list imagemagick &>/dev/null; then
  echo "ImageMagickをインストールします..."
  brew install imagemagick ghostscript little-cms2
fi

# -----------------------------------------------------------------------
# [4/5] バックエンドのビルド (PyInstaller)
# -----------------------------------------------------------------------
echo "[4/5] バックエンドのビルド (PyInstaller)..."
cd "$REPO_ROOT/backend"

# Poetryのインストール（Python 3.11環境に対して）
if ! "$PYTHON311" -m poetry --version &>/dev/null 2>&1; then
  if ! command -v poetry &>/dev/null; then
    echo "Poetryをインストールします..."
    "$PYTHON311" -m pip install poetry==1.8.2
  fi
fi

# poetry コマンドを解決
POETRY_CMD=""
if command -v poetry &>/dev/null; then
  POETRY_CMD="poetry"
elif "$PYTHON311" -m poetry --version &>/dev/null 2>&1; then
  POETRY_CMD="$PYTHON311 -m poetry"
else
  "$PYTHON311" -m pip install poetry==1.8.2
  POETRY_CMD="$PYTHON311 -m poetry"
fi

# 仮想環境の作成を有効化（前回の実行で無効化されていた場合に備えて）
$POETRY_CMD config virtualenvs.create true

# Python 3.11の仮想環境を使用
$POETRY_CMD env use "$PYTHON311"
$POETRY_CMD install --no-interaction --no-ansi

# PyInstaller を仮想環境内にインストール
$POETRY_CMD run pip install pyinstaller --quiet

# PyInstallerでバイナリビルド（-y で既存の出力ディレクトリを上書き）
$POETRY_CMD run pyinstaller chroma_sync.spec --clean -y

echo "バックエンドビルド完了: backend/dist/chroma_sync/"

# -----------------------------------------------------------------------
# [5/5] フロントエンドのビルド & Electronパッケージ化
# -----------------------------------------------------------------------
echo "[5/5] フロントエンドのビルド & Electronパッケージ化..."
cd "$REPO_ROOT"

npm install
npm run build:frontend

ARCH="${1:-arm64}"  # デフォルトはApple Silicon

case "$ARCH" in
  arm64) npm run dist:mac:arm64 ;;
  x64)   npm run dist:mac:x64 ;;
  all)   npm run dist:mac ;;
  *)
    echo "不明なアーキテクチャ: $ARCH (arm64 / x64 / all)"
    exit 1
    ;;
esac

echo ""
echo "=== ビルド完了 ==="
echo "出力先: dist-electron/"
ls -la "$REPO_ROOT/dist-electron/" 2>/dev/null || true
