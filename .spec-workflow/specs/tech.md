# Technology Stack

## Project Type

ローカルおよびWeb上で動作するJPEG変換Webアプリケーション。Docker環境でのローカル実行と、クラウドへのデプロイの両方に対応。

## Core Technologies

### Primary Language(s)
- **Language**: Python 3.11
- **Runtime**: CPython
- **Language-specific tools**: pip, Poetry（パッケージ管理）

### Key Dependencies/Libraries

#### 画像処理・変換
- **Pillow (PIL Fork)**: 基本的な画像処理・フォーマット変換
- **python-psd**: PSDファイルの読み込みとカラープロファイル取得
- **ImageMagick (wand)**: ai/psdファイルの高品質変換・カラープロファイル処理
- **littlecms2 (lcms2)**: ICCカラープロファイル変換エンジン（色味保持の核心）
- **scikit-image**: 色差計算（ΔE値）と画像比較

#### Webフレームワーク
- **FastAPI**: バックエンドAPIサーバー（非同期処理対応）
- **Uvicorn**: ASGIサーバー
- **React**: フロントエンドUI（TypeScript）
- **Vite**: フロントエンドビルドツール

#### ファイル処理
- **python-multipart**: マルチパートファイルアップロード処理
- **aiofiles**: 非同期ファイルI/O

### Application Architecture

クライアント・サーバーアーキテクチャ：
- **フロントエンド**: React SPA（Single Page Application）
- **バックエンドAPI**: FastAPI（REST API）
- **変換エンジン**: Python処理モジュール（ImageMagick + lcms2）
- **キュー**: asyncio ベースの非同期タスクキュー（シンプルな実装）

```
[React Frontend]
      ↕ REST API / WebSocket
[FastAPI Backend]
      ↕
[Conversion Engine]
  ├── ImageMagick/Wand (変換)
  ├── lcms2 (カラープロファイル)
  └── scikit-image (色差計算)
```

### Data Storage
- **一時ファイル**: ローカルファイルシステム（変換処理中のみ保持）
- **変換ログ**: SQLite（ローカル環境）/ Firebase Firestore（Web版）
- **Data formats**: JSON（API通信）、JPEG/PNG（画像）

### External Integrations
- **Firebase**: 認証・データストレージ（Web版のみ）
- **Protocols**: HTTP/REST, WebSocket（進捗通知）

### Monitoring & Dashboard Technologies
- **Real-time Communication**: WebSocket（変換進捗のリアルタイム通知）
- **State Management**: React Context + hooks

## Development Environment

### Build & Development Tools
- **Build System**: Docker Compose（Compose v2、compose.yaml使用）
- **Package Management**: Poetry（Python）、npm（Node.js）
- **Development workflow**: ホットリロード（バックエンド: watchfiles、フロントエンド: Vite HMR）

### Code Quality Tools
- **Static Analysis**: 
  - Python: ruff（linting）、mypy（型チェック）
  - TypeScript: ESLint
- **Formatting**: black（Python）、Prettier（TypeScript）
- **Testing Framework**: 
  - Python: pytest + pytest-asyncio
  - TypeScript: Vitest
- **Documentation**: docstring（Python）、JSDoc（TypeScript）

### Version Control & Collaboration
- **VCS**: Git
- **Branching Strategy**: GitHub Flow（feature branch → main）
- **Code Review Process**: GitHub Pull Request

## Deployment & Distribution

- **Target Platform(s)**: 
  - ローカル: Docker Desktop（Mac/Windows/Linux）
  - Web: Firebase Hosting + Cloud Run
- **Distribution Method**: Docker Compose（ローカル）、Firebase deploy（Web）
- **Installation Requirements**: Docker Desktop、Node.js（開発時のみ）
- **Update Mechanism**: docker pull / git pull + docker compose up

## Technical Requirements & Constraints

### Performance Requirements
- A4サイズ（2480×3508px、300dpi）の1ファイル変換: 30秒以内
- バッチ処理: 最大10ファイルの同時処理対応
- メモリ使用量: 1ファイルあたり最大1GB

### Compatibility Requirements
- **Platform Support**: macOS 13+, Windows 10+, Linux (Ubuntu 20.04+)
- **Docker**: Docker Engine 24.0+
- **Browser Support**: Chrome 100+, Firefox 100+, Safari 16+

### Security & Compliance
- **Security Requirements**: 
  - アップロードファイルは変換完了後24時間で自動削除
  - ファイルアクセスはセッション単位で制限
- **Threat Model**: ファイルアップロードによるRCE防止（ファイル形式の厳密な検証）

### Scalability & Reliability
- **Expected Load**: ローカル版は単一ユーザー、Web版は同時10ユーザーを想定
- **Availability Requirements**: Web版: 99%以上
- **Growth Projections**: 将来的にCloud Runでオートスケール対応

## Technical Decisions & Rationale

### Decision Log

1. **ImageMagick + lcms2 の採用**: 
   - Pillowだけではカラープロファイル変換の精度が不十分なため、ImageMagickとlittlecms2を組み合わせて使用
   - lcms2は業界標準のICCカラープロファイル処理ライブラリ

2. **FastAPI の採用**: 
   - 非同期処理に対応しており、ファイル変換中も他のリクエストを受け付けられる
   - WebSocketのサポートが標準で備わっており、変換進捗の通知に活用できる

3. **Docker Composeでの環境構築**:
   - ImageMagickなどのシステム依存関係をDockerでカプセル化
   - 開発環境の統一化

## Known Limitations

- **大容量ファイル**: 100MBを超えるファイルは変換に時間がかかる可能性がある
- **ai形式の制限**: 一部の高度なIllustrator機能（3Dエフェクト等）は変換後に外観が変わる場合がある
