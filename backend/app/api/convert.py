import asyncio
import json
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from app.config import settings
from app.models.job import ConversionOptions
from app.services.file_manager import FileManager
from app.services.job_queue import JobQueue

router = APIRouter()
ws_router = APIRouter()  # /api プレフィックスなしで登録する WebSocket 専用ルーター
job_queue = JobQueue()
file_manager = FileManager(settings.upload_dir)

ALLOWED_EXTENSIONS = {".ai", ".psd"}
ALLOWED_CONTENT_TYPES = {
    "application/postscript",
    "application/illustrator",
    "image/vnd.adobe.photoshop",
    "application/octet-stream",  # 一部のシステムはこれで送る
    "application/pdf",  # macOS は AI ファイルを PDF として送ることがある
    "application/x-photoshop",
}


def _validate_file(filename: str) -> None:
    """ファイル名の拡張子を検証する"""
    from pathlib import Path

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"対応していないファイル形式です。対応形式: {', '.join(ALLOWED_EXTENSIONS)}",
        )


@router.post("/convert")
async def start_conversion(
    file: UploadFile = File(...),
    target_size_kb: int | None = Form(None),
    quality: int = Form(settings.default_quality),
    max_delta_e: float = Form(settings.max_delta_e),
    use_llm: bool = Form(False),
) -> dict[str, Any]:
    """ファイルをアップロードして変換ジョブを開始する"""
    _validate_file(file.filename or "")

    # ファイルサイズチェック
    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"ファイルサイズが大きすぎます。{settings.max_upload_size_mb}MB以下のファイルをご使用ください",
        )

    # ファイルを保存
    input_path = await file_manager.save_upload(content, file.filename or "upload")

    # 変換オプション
    options = ConversionOptions(
        target_size_kb=target_size_kb,
        quality=quality,
        max_delta_e=max_delta_e,
        use_llm=use_llm,
    )

    # ジョブをキューに追加
    job = await job_queue.enqueue(input_path, options)

    return {"job_id": job.job_id, "status": job.status}


@router.get("/convert/{job_id}/status")
async def get_conversion_status(job_id: str) -> dict[str, Any]:
    """変換ジョブの状態を取得する"""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")

    result = {
        "job_id": job.job_id,
        "status": job.status,
        "created_at": job.created_at.isoformat(),
    }
    if job.completed_at:
        result["completed_at"] = job.completed_at.isoformat()
    if job.error:
        result["error"] = job.error
    if job.delta_e is not None:
        result["delta_e"] = job.delta_e

    return result


@router.get("/convert/{job_id}/result")
async def get_conversion_result(job_id: str) -> dict[str, Any]:
    """変換結果の詳細を取得する"""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"変換がまだ完了していません: {job.status}")

    result = job_queue.get_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="変換結果が見つかりません")

    return {
        "job_id": result.job_id,
        "success": result.success,
        "original_size_bytes": result.original_size_bytes,
        "output_size_bytes": result.output_size_bytes,
        "delta_e": result.delta_e,
        "corrections_applied": result.corrections_applied,
        "correction_regions_count": len(result.correction_regions),
    }


@router.get("/convert/{job_id}/download")
async def download_result(job_id: str) -> FileResponse:
    """変換後のJPEGファイルをダウンロードする"""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")

    if job.status != "completed" or not job.output_file_path:
        raise HTTPException(status_code=400, detail="変換がまだ完了していません")

    import os

    if not os.path.exists(job.output_file_path):
        raise HTTPException(status_code=404, detail="変換ファイルが見つかりません")

    from pathlib import Path

    filename = Path(job.input_file_path).stem + ".jpg"
    return FileResponse(
        job.output_file_path,
        media_type="image/jpeg",
        filename=filename,
    )


@router.get("/convert/{job_id}/preview")
async def get_preview(job_id: str) -> FileResponse:
    """変換後のJPEGプレビューを返す"""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")

    if job.status != "completed" or not job.output_file_path:
        raise HTTPException(status_code=400, detail="変換がまだ完了していません")

    import os

    if not os.path.exists(job.output_file_path):
        raise HTTPException(status_code=404, detail="変換ファイルが見つかりません")

    return FileResponse(job.output_file_path, media_type="image/jpeg")


@ws_router.websocket("/ws/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str) -> None:
    """WebSocketで変換進捗をリアルタイム通知する"""
    await websocket.accept()

    try:
        while True:
            job = job_queue.get_job(job_id)
            if not job:
                await websocket.send_text(json.dumps({"error": "ジョブが見つかりません"}))
                break

            progress_data = {
                "job_id": job.job_id,
                "status": job.status,
                "progress": job.progress,
                "message": job.progress_message,
            }

            if job.delta_e is not None:
                progress_data["delta_e"] = job.delta_e
            if job.error:
                progress_data["error"] = job.error

            await websocket.send_text(json.dumps(progress_data))

            if job.status in ("completed", "failed"):
                break

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass
