import io
import uuid
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

from app.config import settings
from app.models.job import ConversionOptions
from app.services.file_manager import FileManager
from app.services.job_queue import JobQueue

router = APIRouter()
job_queue = JobQueue()
file_manager = FileManager(settings.upload_dir)

ALLOWED_EXTENSIONS = {".ai", ".psd"}


def _validate_file(filename: str) -> None:
    """ファイル名の拡張子を検証する"""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"対応していないファイル形式です。対応形式: {', '.join(ALLOWED_EXTENSIONS)}",
        )


@router.post("/presign-upload")
async def presign_upload(
    filename: str = Form(...),
) -> dict[str, Any]:
    """S3への直接アップロード用の署名付きURLを返す（API Gateway 10MB 制限回避用）。

    大きなファイル（>8MB）はこのエンドポイントで URL を取得し、
    クライアントから直接 S3 に PUT してから /convert に s3_key を渡す。
    """
    if not settings.use_aws:
        raise HTTPException(status_code=400, detail="ローカルモードでは使用できません")

    _validate_file(filename)

    from app.services.storage import S3Storage

    storage = S3Storage(settings.s3_bucket, settings.aws_region)
    job_id = str(uuid.uuid4())
    upload_url, s3_key = storage.generate_presigned_upload_url(filename, job_id)

    return {"upload_url": upload_url, "s3_key": s3_key, "job_id": job_id}


@router.post("/convert")
async def start_conversion(
    file: UploadFile | None = File(default=None),
    s3_key: str | None = Form(default=None),
    original_filename: str | None = Form(default=None),
    target_size_kb: int | None = Form(None),
    quality: int = Form(settings.default_quality),
    max_delta_e: float = Form(settings.max_delta_e),
) -> dict[str, Any]:
    """ファイルをアップロードして変換ジョブを開始する。

    2つのモードをサポート:
    1. 直接アップロード: file パラメータでファイルを送信（最大 8MB）
    2. S3キー指定: /presign-upload で取得した s3_key を指定（大きなファイル用）
    """
    options = ConversionOptions(
        target_size_kb=target_size_kb,
        quality=quality,
        max_delta_e=max_delta_e,
    )

    if settings.use_aws:
        from app.services.storage import S3Storage

        storage = S3Storage(settings.s3_bucket, settings.aws_region)

        if s3_key:
            # Presigned URL アップロード済みファイルをそのまま使用
            if not original_filename:
                raise HTTPException(status_code=422, detail="original_filename が必要です")
            _validate_file(original_filename)
            job = await job_queue.enqueue(s3_key, options, original_filename)
        elif file is not None:
            # 直接アップロード（8MB 以下）
            _validate_file(file.filename or "")
            content = await file.read()
            if len(content) > settings.max_upload_size_mb * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail=f"ファイルサイズが大きすぎます。{settings.max_upload_size_mb}MB以下のファイルをご使用ください",
                )
            fname = file.filename or "upload"
            job_id = str(uuid.uuid4())
            input_s3_key = await storage.save_upload(content, fname, job_id)
            job = await job_queue.enqueue(input_s3_key, options, fname)
        else:
            raise HTTPException(status_code=422, detail="file または s3_key を指定してください")
    else:
        # ローカルモード
        if file is None:
            raise HTTPException(status_code=422, detail="ローカルモードでは file が必要です")
        _validate_file(file.filename or "")
        content = await file.read()
        if len(content) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"ファイルサイズが大きすぎます。{settings.max_upload_size_mb}MB以下のファイルをご使用ください",
            )
        input_path = await file_manager.save_upload(content, file.filename or "upload")
        job = await job_queue.enqueue(input_path, options, file.filename or "upload")

    return {"job_id": job.job_id, "status": job.status}


@router.get("/convert/{job_id}/status")
async def get_conversion_status(job_id: str) -> dict[str, Any]:
    """変換ジョブの状態を取得する"""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")

    result: dict[str, Any] = {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.progress_message,
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
async def download_result(job_id: str) -> FileResponse | RedirectResponse:
    """変換後のJPEGファイルをダウンロードする。AWSモードではS3署名付きURLにリダイレクト"""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")

    if job.status != "completed" or not job.output_file_path:
        raise HTTPException(status_code=400, detail="変換がまだ完了していません")

    if settings.use_aws:
        from app.services.storage import S3Storage

        storage = S3Storage(settings.s3_bucket, settings.aws_region)
        if not storage.object_exists(job.output_file_path):
            raise HTTPException(status_code=404, detail="変換ファイルが見つかりません")
        url = storage.generate_presigned_url(job.output_file_path, expires_in=300)
        return RedirectResponse(url=url, status_code=302)
    else:
        import os

        if not os.path.exists(job.output_file_path):
            raise HTTPException(status_code=404, detail="変換ファイルが見つかりません")
        download_name = Path(job.original_filename).stem + ".jpg"
        return FileResponse(job.output_file_path, media_type="image/jpeg", filename=download_name)


@router.get("/convert/{job_id}/preview")
async def get_preview(job_id: str) -> FileResponse | RedirectResponse:
    """変換後のJPEGプレビューを返す。AWSモードではS3署名付きURLにリダイレクト"""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")

    if job.status != "completed" or not job.output_file_path:
        raise HTTPException(status_code=400, detail="変換がまだ完了していません")

    if settings.use_aws:
        from app.services.storage import S3Storage

        storage = S3Storage(settings.s3_bucket, settings.aws_region)
        if not storage.object_exists(job.output_file_path):
            raise HTTPException(status_code=404, detail="変換ファイルが見つかりません")
        url = storage.generate_presigned_url(job.output_file_path, expires_in=3600)
        return RedirectResponse(url=url, status_code=302)
    else:
        import os

        if not os.path.exists(job.output_file_path):
            raise HTTPException(status_code=404, detail="変換ファイルが見つかりません")
        return FileResponse(job.output_file_path, media_type="image/jpeg")


@router.get("/convert/batch-download")
async def batch_download_results(job_ids: list[str] = Query(...)) -> StreamingResponse:
    """複数の変換結果をZIPファイルとしてまとめてダウンロードする"""
    if not job_ids:
        raise HTTPException(status_code=400, detail="job_ids を指定してください")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if settings.use_aws:
            import os
            import tempfile

            from app.services.storage import S3Storage

            storage = S3Storage(settings.s3_bucket, settings.aws_region)
            with tempfile.TemporaryDirectory() as tmpdir:
                for job_id in job_ids:
                    job = job_queue.get_job(job_id)
                    if not job or job.status != "completed" or not job.output_file_path:
                        continue
                    if not storage.object_exists(job.output_file_path):
                        continue
                    tmp_path = os.path.join(tmpdir, f"{job_id}.jpg")
                    storage.download_to_path(job.output_file_path, tmp_path)
                    arcname = Path(job.original_filename).stem + ".jpg"
                    zf.write(tmp_path, arcname)
        else:
            import os

            for job_id in job_ids:
                job = job_queue.get_job(job_id)
                if not job or job.status != "completed" or not job.output_file_path:
                    continue
                if not os.path.exists(job.output_file_path):
                    continue
                arcname = Path(job.original_filename).stem + ".jpg"
                zf.write(job.output_file_path, arcname)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=chroma-sync-results.zip"},
    )
