from pydantic import BaseModel


class Region(BaseModel):
    """色補正が適用された領域"""

    x: int
    """領域の左上X座標"""

    y: int
    """領域の左上Y座標"""

    width: int
    """領域の幅"""

    height: int
    """領域の高さ"""

    delta_e_before: float
    """補正前のΔE値"""

    delta_e_after: float
    """補正後のΔE値"""


class ConversionResult(BaseModel):
    """変換結果"""

    job_id: str
    """対応するジョブID"""

    success: bool
    """変換成功フラグ"""

    output_path: str | None = None
    """変換後のJPEGファイルパス"""

    original_size_bytes: int
    """元ファイルのサイズ（バイト）"""

    output_size_bytes: int
    """変換後ファイルのサイズ（バイト）"""

    delta_e: float
    """最終的な色差値（ΔE）"""

    corrections_applied: bool
    """自動色補正が適用されたか"""

    correction_regions: list[Region] = []
    """色補正が適用された領域のリスト"""
