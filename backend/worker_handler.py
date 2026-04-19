"""Worker Lambda エントリーポイント。

SQSから変換ジョブを受け取り、ImageMagickで変換処理を実行する。
"""
import json
import logging
import os
import tempfile
from datetime import datetime

from app.config import settings
from app.converter.engine import ConversionEngine
from app.models.job import ConversionJob, ConversionOptions
from app.services.job_repository import JobRepository
from app.services.storage import S3Storage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event: dict, context: object) -> dict:
    """SQSイベントから変換ジョブを処理する。"""
    repo = JobRepository(settings.dynamodb_table, settings.file_retention_hours)
    storage = S3Storage(settings.s3_bucket, settings.aws_region)
    engine = ConversionEngine()

    failed_message_ids = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")
        try:
            body = json.loads(record["body"])
            _process_job(body, repo, storage, engine)
        except Exception:
            logger.exception("メッセージ %s の処理中にエラーが発生しました", message_id)
            failed_message_ids.append({"itemIdentifier": message_id})

    # SQSのバッチ処理失敗レポート（部分的な失敗を返す）
    return {"batchItemFailures": [{"itemIdentifier": mid} for mid in failed_message_ids]}


def _process_job(
    body: dict,
    repo: JobRepository,
    storage: S3Storage,
    engine: ConversionEngine,
) -> None:
    """1件のジョブを処理する。"""
    job_id = body["job_id"]
    input_s3_key = body["input_s3_key"]
    original_filename = body.get("original_filename", "upload")
    options_raw = body.get("options", {})

    options = ConversionOptions(
        target_size_kb=options_raw.get("target_size_kb"),
        quality=int(options_raw.get("quality", settings.default_quality)),
        max_delta_e=float(options_raw.get("max_delta_e", settings.max_delta_e)),
    )

    # 処理中に更新
    repo.update_job_status(
        job_id=job_id,
        status="processing",
        progress=5,
        progress_message="変換処理を開始しています...",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # S3から入力ファイルをダウンロード
        input_ext = os.path.splitext(input_s3_key)[1] or ".ai"
        input_path = os.path.join(tmpdir, f"input{input_ext}")
        output_path = os.path.join(tmpdir, "output.jpg")

        repo.update_job_status(
            job_id=job_id,
            status="processing",
            progress=10,
            progress_message="ファイルをダウンロード中...",
        )
        storage.download_to_path(input_s3_key, input_path)

        # ダミーのConversionJobを作成（進捗コールバック用）
        job = ConversionJob(
            job_id=job_id,
            input_file_path=input_path,
            original_filename=original_filename,
            options=options,
            status="processing",
        )

        try:
            repo.update_job_status(
                job_id=job_id,
                status="processing",
                progress=20,
                progress_message="変換処理中...",
            )

            result = engine.convert(input_path, output_path, options, job)

            # 変換結果をS3にアップロード
            output_s3_key = storage.get_output_key(job_id)
            repo.update_job_status(
                job_id=job_id,
                status="processing",
                progress=90,
                progress_message="変換結果をアップロード中...",
            )
            storage.upload_from_path(output_path, output_s3_key)

            # DynamoDBに結果を保存
            repo.save_result(job_id, result)
            repo.update_job_status(
                job_id=job_id,
                status="completed",
                progress=100,
                progress_message="変換完了",
                output_s3_key=output_s3_key,
                delta_e=result.delta_e,
                corrections_applied=result.corrections_applied,
            )

            logger.info("ジョブ %s の変換が完了しました（ΔE: %.2f）", job_id, result.delta_e)

        except MemoryError:
            error_msg = f"ファイルサイズが大きすぎます。{settings.max_upload_size_mb}MB以下のファイルをご使用ください"
            repo.update_job_status(
                job_id=job_id,
                status="failed",
                progress=0,
                progress_message="変換失敗",
                error=error_msg,
            )
            storage.delete_object(input_s3_key)

        except Exception as e:
            logger.exception("ジョブ %s の変換中にエラーが発生しました", job_id)
            error_detail = str(e) if str(e) else type(e).__name__
            repo.update_job_status(
                job_id=job_id,
                status="failed",
                progress=0,
                progress_message="変換失敗",
                error=f"変換中にエラーが発生しました: {error_detail}",
            )
            storage.delete_object(input_s3_key)
