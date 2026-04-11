import asyncio
import uuid
from datetime import datetime

from app.config import settings
from app.converter.engine import ConversionEngine
from app.models.job import ConversionJob, ConversionOptions
from app.models.result import ConversionResult
from app.services.file_manager import FileManager


class JobQueue:
    """変換ジョブキュー管理クラス"""

    def __init__(self) -> None:
        self._jobs: dict[str, ConversionJob] = {}
        self._results: dict[str, ConversionResult] = {}
        self._engine = ConversionEngine()
        self._file_manager = FileManager(settings.upload_dir)

    async def enqueue(self, input_path: str, options: ConversionOptions) -> ConversionJob:
        """変換ジョブをキューに追加し、非同期で処理を開始する。

        Args:
            input_path: 入力ファイルのパス
            options: 変換オプション

        Returns:
            作成されたジョブ
        """
        job_id = str(uuid.uuid4())
        job = ConversionJob(
            job_id=job_id,
            input_file_path=input_path,
            options=options,
        )
        self._jobs[job_id] = job

        # 非同期でジョブを処理
        asyncio.create_task(self._process_job(job))

        return job

    async def _process_job(self, job: ConversionJob) -> None:
        """ジョブを処理する（バックグラウンドタスク）。

        Args:
            job: 処理するジョブ
        """
        job.status = "processing"
        job.progress = 5
        job.progress_message = "変換処理を開始しています..."

        output_path = self._file_manager.get_output_path(job.input_file_path, job.job_id)

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

        except Exception as e:
            job.status = "failed"
            job.error = f"変換中にエラーが発生しました: {str(e)}"
            job.progress_message = "変換失敗"
            job.completed_at = datetime.utcnow()

    def get_job(self, job_id: str) -> ConversionJob | None:
        """ジョブを取得する。

        Args:
            job_id: ジョブID

        Returns:
            ジョブ（存在しない場合はNone）
        """
        return self._jobs.get(job_id)

    def get_result(self, job_id: str) -> ConversionResult | None:
        """変換結果を取得する。

        Args:
            job_id: ジョブID

        Returns:
            変換結果（存在しない場合はNone）
        """
        return self._results.get(job_id)
