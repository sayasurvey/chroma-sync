# Project Structure

## Directory Organization

```
chroma-sync/
├── compose.yaml              # Docker Compose 設定（公式推奨）
├── .env.example              # 環境変数テンプレート
├── .gitignore
├── README.md
├── CLAUDE.md
│
├── backend/                  # FastAPI バックエンド
│   ├── Dockerfile
│   ├── pyproject.toml        # Poetry 設定
│   ├── app/
│   │   ├── main.py           # FastAPIアプリケーションのエントリーポイント
│   │   ├── api/              # APIルーター
│   │   │   ├── __init__.py
│   │   │   ├── convert.py    # 変換関連エンドポイント
│   │   │   └── health.py     # ヘルスチェック
│   │   ├── converter/        # 変換エンジン（コアロジック）
│   │   │   ├── __init__.py
│   │   │   ├── engine.py     # ConversionEngine メインクラス
│   │   │   ├── color_profile.py  # ColorProfileManager
│   │   │   └── color_diff.py     # ColorDiffCalculator
│   │   ├── models/           # Pydantic データモデル
│   │   │   ├── __init__.py
│   │   │   ├── job.py        # ConversionJob, ConversionOptions
│   │   │   └── result.py     # ConversionResult, Region
│   │   ├── services/         # ビジネスロジック
│   │   │   ├── __init__.py
│   │   │   ├── job_queue.py  # 変換ジョブキュー管理
│   │   │   └── file_manager.py   # アップロードファイル管理
│   │   └── config.py         # アプリケーション設定
│   └── tests/                # テストコード
│       ├── conftest.py
│       ├── test_converter/
│       │   ├── test_engine.py
│       │   ├── test_color_profile.py
│       │   └── test_color_diff.py
│       └── test_api/
│           └── test_convert.py
│
├── frontend/                 # React フロントエンド
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx          # エントリーポイント
│       ├── App.tsx           # ルートコンポーネント
│       ├── components/       # UIコンポーネント
│       │   ├── FileUpload/   # ファイルアップロードコンポーネント
│       │   │   ├── index.tsx
│       │   │   └── FileUpload.module.css
│       │   ├── ConversionOptions/  # 変換オプション設定UI
│       │   │   └── index.tsx
│       │   ├── ProgressBar/  # 変換進捗表示
│       │   │   └── index.tsx
│       │   └── ResultPreview/  # 変換結果プレビュー
│       │       ├── index.tsx
│       │       └── ColorDiffMap.tsx  # 色差マップ表示
│       ├── hooks/            # カスタムReact hooks
│       │   ├── useConversion.ts    # 変換処理フック
│       │   └── useWebSocket.ts     # WebSocket接続フック
│       ├── api/              # APIクライアント
│       │   └── client.ts     # axios/fetch ラッパー
│       └── types/            # TypeScript型定義
│           └── conversion.ts
│
└── .spec-workflow/           # spec-workflow 仕様書管理
    ├── specs/
    │   ├── product.md
    │   ├── requirements.md
    │   ├── tech.md
    │   ├── design.md
    │   └── structure.md
    └── templates/            # spec-workflow テンプレート
```

## Naming Conventions

### Files
- **Pythonモジュール**: `snake_case` （例: `color_profile.py`, `job_queue.py`）
- **Reactコンポーネント**: `PascalCase` ディレクトリ内の `index.tsx`（例: `FileUpload/index.tsx`）
- **TypeScriptユーティリティ**: `camelCase`（例: `useConversion.ts`）
- **Pythonテスト**: `test_[module_name].py`（例: `test_engine.py`）

### Code
- **Python クラス**: `PascalCase`（例: `ConversionEngine`, `ColorDiffCalculator`）
- **Python 関数・メソッド**: `snake_case`（例: `calculate_delta_e`, `convert_to_srgb`）
- **Python 定数**: `UPPER_SNAKE_CASE`（例: `DEFAULT_QUALITY`, `MAX_DELTA_E`）
- **TypeScript インターフェース/型**: `PascalCase`（例: `ConversionJob`, `ConversionOptions`）
- **TypeScript 関数**: `camelCase`（例: `startConversion`, `downloadResult`）

## Import Patterns

### Python Import Order
1. 標準ライブラリ（`os`, `pathlib`, `asyncio`）
2. サードパーティライブラリ（`fastapi`, `wand`, `numpy`）
3. 内部モジュール（`app.converter`, `app.models`）
4. 相対インポート（同じパッケージ内）

### TypeScript Import Order
1. React/外部ライブラリ
2. 内部コンポーネント（`@/components/...`）
3. 内部hooks・utilities（`@/hooks/...`, `@/api/...`）
4. 型定義（`@/types/...`）
5. スタイル（`./Component.module.css`）

## Code Structure Patterns

### Python モジュール構成
```python
# 1. インポート
from pathlib import Path
from wand.image import Image

# 2. 定数
DEFAULT_QUALITY = 85
MAX_DELTA_E = 2.0

# 3. 型定義（Pydanticモデルは models/ に分離）

# 4. メインクラス・関数実装
class ConversionEngine:
    def convert(self, ...): ...
    def _internal_helper(self, ...): ...  # プライベートメソッドはプレフィックス _

# 5. エクスポート（__init__.py で管理）
```

### React コンポーネント構成
```typescript
// 1. インポート
import React, { useState } from 'react'
import { useConversion } from '@/hooks/useConversion'

// 2. 型定義（コンポーネントProps）
interface Props {
  onComplete: (result: ConversionResult) => void
}

// 3. コンポーネント実装
export const FileUpload: React.FC<Props> = ({ onComplete }) => {
  // state
  // handlers
  // render
}
```

## Code Organization Principles

1. **Single Responsibility**: 各ファイルは1つの責任を持つ（変換ロジックはUI・APIから独立）
2. **Modularity**: `converter/` モジュールはFastAPIに依存しない純粋なPythonモジュール
3. **Testability**: 依存性注入パターンで変換エンジンをテストしやすく設計
4. **Consistency**: Pythonは`snake_case`、TypeScriptは`camelCase/PascalCase`

## Module Boundaries

- **`converter/` モジュール**: FastAPIや外部フレームワークに依存しない純粋な変換ロジック
- **`api/` ルーター**: HTTPリクエスト処理のみ、ビジネスロジックは`services/`に委譲
- **`services/`**: ビジネスロジック（`converter/`と`api/`の橋渡し）
- **フロントエンド `components/`**: UIのみ、APIロジックは`hooks/`と`api/`に分離

## Code Size Guidelines

- **Pythonファイル**: 最大300行
- **TypeScriptファイル（コンポーネント）**: 最大200行
- **関数・メソッド**: 最大50行
- **ネスト深度**: 最大4階層

## Documentation Standards
- Python パブリックメソッド: docstring 必須（Args, Returns, Raises を記載）
- TypeScript コンポーネント: Props インターフェースにコメント
- 複雑なアルゴリズム（色差計算、プロファイル変換）: インラインコメントで解説
- 主要モジュールには `README.md` を配置
