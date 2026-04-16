# chroma-sync

Adobe Illustrator（.ai）や Adobe Photoshop（.psd）ファイルを JPEG に変換する際に発生する**色ずれを自動検出・修正**するアプリケーションです。

## 概要

ai/psd ファイルを JPEG に変換すると、カラープロファイルの不一致によって色味が変化してしまう場合があります。chroma-sync はこの問題を解決するため、以下の処理を自動で行います。

1. ICCカラープロファイルを維持したまま JPEG に変換
2. 変換前後の色差（ΔE）を計算し、色ずれが発生していないか確認
3. 色ずれ（ΔE ≥ 2.0）が検出された場合、該当箇所を自動補正

ローカル環境および Web 上で動作し、変換後の再調整作業を不要にします。

## 主な機能

- **色味保持変換**: lcms2 + ImageMagick による高精度なカラープロファイル変換
- **自動色味修正**: 色ずれ領域を検出して自動補正（CIEDE2000規格のΔE値で評価）
- **圧縮率指定**: 目標ファイルサイズまたは JPEG 品質レベル（1〜100）を指定可能
- **バッチ処理**: 複数ファイルの一括変換に対応
- **変換結果プレビュー**: 変換前後の比較表示と色差マップ

## 対応ファイル形式

| 入力 | 出力 |
|------|------|
| .ai（Adobe Illustrator） | .jpg（JPEG） |
| .psd（Adobe Photoshop） | |

## 技術スタック

| 領域 | 技術 |
|------|------|
| バックエンド | Python 3.11 + FastAPI |
| フロントエンド | React + TypeScript（Vite） |
| 画像変換 | ImageMagick（Wand） |
| カラープロファイル | lcms2（LittleCMS2） |
| 色差計算 | scikit-image（CIEDE2000） |
| 環境構築 | Docker（compose.yaml） |

## デスクトップアプリ（インストーラー）

GitHubの [Releases](https://github.com/sayasurvey/chroma-sync/releases) から最新版をダウンロードできます。

| OS | ファイル | 対応アーキテクチャ |
|----|----------|--------------------|
| macOS | `ChromaSync-*.dmg` | Apple Silicon (arm64) / Intel (x64) |
| Windows | `ChromaSync-Setup-*.exe` | x64 |

### macOS
1. `ChromaSync-*-arm64.dmg`（Apple Silicon）または `ChromaSync-*-x64.dmg`（Intel）をダウンロード
2. DMGを開き、ChromaSync.appを `/Applications` にドラッグ
3. 初回起動時は右クリック → 「開く」を選択（未署名アプリの警告回避）

### Windows
1. `ChromaSync-Setup-*.exe` をダウンロードして実行
2. インストールウィザードの指示に従う

## 開発環境のセットアップ

### 必要なもの

- Docker Desktop 24.0+

### 起動方法

```bash
# リポジトリをクローン
git clone https://github.com/sayasurvey/chroma-sync.git
cd chroma-sync

# 環境変数を設定
cp .env.example .env

# 起動
docker compose up
```

ブラウザで `http://localhost:5173` にアクセスしてください。

## デスクトップアプリのビルド方法

デスクトップアプリ（Electron）をローカルでビルドする場合の手順です。

### macOS（Apple Silicon / Intel）

```bash
# 前提: Homebrew, Python 3.11, Node.js 20 がインストール済みであること

# arm64（Apple Silicon）向けビルド
./scripts/build-mac.sh arm64

# x64（Intel Mac）向けビルド
./scripts/build-mac.sh x64

# 両アーキテクチャのユニバーサルビルド
./scripts/build-mac.sh all
```

出力先: `dist-electron/`

### Windows

PowerShellで実行します。前提として [ImageMagick Q16-HDRI x64](https://imagemagick.org/script/download.php) のインストールが必要です。

```powershell
# ImageMagickのインストールパスを環境変数に設定
$env:MAGICK_HOME = "C:\Program Files\ImageMagick-7.1.1-Q16-HDRI"

.\scripts\build-win.ps1
```

出力先: `dist-electron\`

### GitHub Actionsによる自動ビルド

`v*` タグをプッシュすると自動でmacOS/Windowsのバイナリがビルドされ、GitHub Releaseが作成されます。

```bash
git tag v0.1.0
git push origin v0.1.0
```

## 色差の基準

本アプリでは CIEDE2000 規格の ΔE 値を使用して色ずれを評価しています。

| ΔE 値 | 評価 |
|--------|------|
| < 1.0 | 人間がほぼ知覚できない差 |
| < 2.0 | 許容範囲内（本アプリの目標） |
| 2.0 〜 | 自動色補正を適用 |
