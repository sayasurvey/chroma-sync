from datetime import datetime

from pydantic import BaseModel, Field


class ConversionOptions(BaseModel):
    """変換オプション"""

    target_size_kb: int | None = None
    """目標ファイルサイズ（KB）。指定した場合は品質より優先される"""

    quality: int = Field(default=85, ge=1, le=100)
    """JPEG品質 (1-100)"""

    max_delta_e: float = Field(default=2.0, gt=0)
    """許容する最大色差（ΔE）"""


class ConversionJob(BaseModel):
    """変換ジョブ"""

    job_id: str
    """ジョブの一意識別子（UUID）"""

    status: str = "pending"
    """ジョブの状態: "pending" | "processing" | "completed" | "failed" """

    input_file_path: str
    """アップロードされたファイルのパス"""

    output_file_path: str | None = None
    """変換後のJPEGファイルパス"""

    options: ConversionOptions
    """変換オプション"""

    delta_e: float | None = None
    """最終的な色差値（ΔE）"""

    corrections_applied: bool = False
    """自動色補正が適用されたか"""

    progress: int = 0
    """進捗率 (0-100)"""

    progress_message: str = "待機中..."
    """進捗メッセージ"""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    """ジョブ作成時刻"""

    completed_at: datetime | None = None
    """ジョブ完了時刻"""

    error: str | None = None
    """エラーメッセージ（失敗時）"""
