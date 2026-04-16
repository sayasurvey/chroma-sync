# Windows向けのChromaSync デスクトップアプリビルドスクリプト
# PowerShellで実行: ./scripts/build-win.ps1
# 前提: Python 3.11, Node.js 20, ImageMagick Q16-HDRI がインストール済みであること

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Set-Location $RepoRoot

Write-Host "=== ChromaSync Windows ビルド開始 ===" -ForegroundColor Cyan

# --- ImageMagickの確認 ---
Write-Host "[1/4] ImageMagickの確認..." -ForegroundColor Yellow
$MagickHome = $env:MAGICK_HOME
if (-not $MagickHome) {
    $candidates = @(
        "C:\Program Files\ImageMagick-7.1.1-Q16-HDRI",
        "C:\Program Files\ImageMagick-7.1.0-Q16-HDRI",
        "C:\Program Files\ImageMagick-7.0.11-Q16-HDRI"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) {
            $MagickHome = $path
            break
        }
    }
}
if (-not $MagickHome -or -not (Test-Path $MagickHome)) {
    Write-Host "Error: ImageMagick Q16-HDRIが見つかりません。" -ForegroundColor Red
    Write-Host "https://imagemagick.org/script/download.php からインストールしてください。" -ForegroundColor Red
    Write-Host "インストール後、環境変数 MAGICK_HOME を設定してください。" -ForegroundColor Red
    exit 1
}
Write-Host "ImageMagick検出: $MagickHome" -ForegroundColor Green
$env:MAGICK_HOME = $MagickHome

# --- バックエンドのビルド ---
Write-Host "[2/4] バックエンドのビルド (PyInstaller)..." -ForegroundColor Yellow
Set-Location "$RepoRoot\backend"

# Poetryのインストール確認
if (-not (Get-Command poetry -ErrorAction SilentlyContinue)) {
    pip install poetry==1.8.2
}

# 依存パッケージのインストール
& poetry config virtualenvs.create false
& poetry install --no-interaction --no-ansi

# PyInstallerのインストール
pip install pyinstaller --quiet

# PyInstallerでビルド
& pyinstaller chroma_sync.spec --clean
Write-Host "バックエンドビルド完了: backend\dist\chroma_sync\" -ForegroundColor Green

# --- フロントエンドのビルド ---
Write-Host "[3/4] フロントエンドのビルド..." -ForegroundColor Yellow
Set-Location $RepoRoot

# ルートのnpmパッケージインストール
npm install

# フロントエンドをビルド
$env:ELECTRON_BUILD = "1"
npm run build:frontend
Write-Host "フロントエンドビルド完了: frontend\dist\" -ForegroundColor Green

# --- Electronアプリのパッケージ化 ---
Write-Host "[4/4] Electronアプリのパッケージ化..." -ForegroundColor Yellow
npm run dist:win

Write-Host ""
Write-Host "=== ビルド完了 ===" -ForegroundColor Cyan
Write-Host "出力先: dist-electron\" -ForegroundColor Cyan
if (Test-Path "$RepoRoot\dist-electron") {
    Get-ChildItem "$RepoRoot\dist-electron" | Format-Table Name, Length, LastWriteTime
}
