import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta

import boto3

from app.config import settings
from app.models.job import ConversionJob, ConversionOptions
from app.models.result import ConversionResult
from app.services.file_manager import FileManager

logger = logging.getLogger(__name__)


class JobQueue:
    """変換ジョブキュー管理クラス。

    AWS環境（S3_BUCKET設定あり）ではDynamoDB + SQSを使用する。
    ローカル開発環境ではインメモリ + asyncio.create_taskを使用する。

    Note:
        ローカルモードはインメモリのため、単一プロセス構成（シングルワーカー）のみ対応。
    """

    def __init__(self) -> None:
        self._use_aws = settings.use_aws

        if self._use_aws:
            from app.services.job_repository import JobRepository
            from app.services.storage import S3Storage

            self._repo = JobRepository(settings.dynamodb_table, settings.file_retention_hours)
            self._storage = S3Storage(settings.s3_bucket, settings.aws_region)
            self._sqs = boto3.client("sqs", region_name=settings.aws_region)
        else:
            # ローカル開発用インメモリストレージ
            self._jobs: dict[str, ConversionJob] = {}
            self._results: dict[str, ConversionResult] = {}
            from app.converter.engine import ConversionEngine

            self._engine = ConversionEngine()
            self._file_manager = FileManager(settings.upload_dir)

    async def enqueue(
        self, input_path: str, options: ConversionOptions, original_filename: str = ""
    ) -> ConversionJob:
        """変換ジョブをキューに追加する。

        Args:
            input_path: AWSモードではS3キー、ローカルモードではファイルパス
            options: 変換オプション
            original_filename: アップロード時の元ファイル名

        Returns:
            作成されたジョブ
        """
        job_id = str(uuid.uuid4())
        job = ConversionJob(
            job_id=job_id,
            input_file_path=input_path,
            original_filename=original_filename,
            options=options,
        )

        if self._use_aws:
            self._repo.save_job(job)
            self._sqs.send_message(
                QueueUrl=settings.sqs_queue_url,
                MessageBody=json.dumps({
                    "job_id": job_id,
                    "input_s3_key": input_path,
                    "original_filename": original_filename,
                    "options": {
                        "target_size_kb": options.target_size_kb,
                        "quality": options.quality,
                        "max_delta_e": options.max_delta_e,
                    },
                }),
            )
        else:
            self._jobs[job_id] = job
            asyncio.create_task(self._process_job_local(job))

        return job

    async def _process_job_local(self, job: ConversionJob) -> None:
        """ローカル開発用：バックグラウンドで変換処理を実行する。"""
        job.status = "processing"
        job.progress = 5
        job.progress_message = "変換処理を開始しています..."

        output_path = self._file_manager.get_output_path(job.input_file_path, job.job_id)
        job.output_file_path = output_path

        try:
            result = await asyncio.to_thread(
                self._engine.convert,
                job.input_file_path,
                output_path,
                job.options,
                job,
            )

            self._results[job.job_id] = result
            job.output_file_path = result.output_path
            job.delta_e = result.delta_e
            job.corrections_applied = result.corrections_applied
            job.status = "completed"
            job.progress = 100
            job.progress_message = "変換完了"
            job.completed_at = datetime.utcnow()

        except MemoryError:
            job.status = "failed"
            job.error = (
                f"ファイルサイズが大きすぎます。{settings.max_upload_size_mb}MB以下のファイルをご使用ください"
            )
            job.progress_message = "変換失敗"
            job.completed_at = datetime.utcnow()
            self._file_manager.delete_file(job.input_file_path)
            self._file_manager.delete_file(output_path)

        except Exception:
            logger.exception("ジョブ %s の変換中にエラーが発生しました", job.job_id)
            job.status = "failed"
            job.error = "変換中にエラーが発生しました。しばらく経ってから再度お試しください。"
            job.progress_message = "変換失敗"
            job.completed_at = datetime.utcnow()
            self._file_manager.delete_file(job.input_file_path)
            self._file_manager.delete_file(output_path)

    def get_job(self, job_id: str) -> ConversionJob | None:
        """ジョブを取得する。"""
        if self._use_aws:
            return self._repo.get_job(job_id)
        return self._jobs.get(job_id)

    def get_result(self, job_id: str) -> ConversionResult | None:
        """変換結果を取得する。"""
        if self._use_aws:
            return self._repo.get_result(job_id)
        return self._results.get(job_id)

    def cleanup_expired_jobs(self, retention_hours: int) -> int:
        """ローカルモード：期限切れジョブをメモリから削除する。AWSモードはDynamoDB TTLに委譲。"""
        if self._use_aws:
            return 0

        threshold = datetime.utcnow() - timedelta(hours=retention_hours)
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status in ("completed", "failed")
            and job.completed_at is not None
            and job.completed_at < threshold
        ]
        for job_id in expired:
            self._jobs.pop(job_id, None)
            self._results.pop(job_id, None)

        if expired:
            logger.info("%d 件の期限切れジョブをメモリから削除しました", len(expired))

        return len(expired)
