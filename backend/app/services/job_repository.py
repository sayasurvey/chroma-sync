import time
from datetime import datetime
from decimal import Decimal
from typing import Any

import boto3

from app.models.job import ConversionJob, ConversionOptions
from app.models.result import ConversionResult, Region


def _to_decimal(value: float | None) -> Decimal | None:
    """floatをDecimalに変換する（DynamoDB用）。"""
    if value is None:
        return None
    return Decimal(str(value))


def _from_decimal(value: Any) -> float | None:
    """DecimalをfloatまたはNoneに変換する。"""
    if value is None:
        return None
    return float(value)


class JobRepository:
    """DynamoDBベースのジョブ状態管理"""

    def __init__(self, table_name: str, retention_hours: int = 24) -> None:
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        self.retention_hours = retention_hours

    def save_job(self, job: ConversionJob) -> None:
        """ジョブをDynamoDBに保存する。"""
        ttl = int(time.time()) + self.retention_hours * 3600
        item: dict[str, Any] = {
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "progress_message": job.progress_message,
            "input_s3_key": job.input_file_path,
            "original_filename": job.original_filename,
            "created_at": job.created_at.isoformat(),
            "corrections_applied": job.corrections_applied,
            "ttl": ttl,
            "options": {
                "quality": job.options.quality,
                "max_delta_e": _to_decimal(job.options.max_delta_e),
            },
        }
        if job.options.target_size_kb is not None:
            item["options"]["target_size_kb"] = job.options.target_size_kb
        if job.output_file_path:
            item["output_s3_key"] = job.output_file_path
        if job.completed_at:
            item["completed_at"] = job.completed_at.isoformat()
        if job.error:
            item["error"] = job.error
        if job.delta_e is not None:
            item["delta_e"] = _to_decimal(job.delta_e)

        self.table.put_item(Item=item)

    def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: int,
        progress_message: str,
        output_s3_key: str | None = None,
        error: str | None = None,
        delta_e: float | None = None,
        corrections_applied: bool | None = None,
    ) -> None:
        """ジョブの状態を部分更新する。"""
        update_expr = "SET #s = :status, progress = :progress, progress_message = :msg"
        expr_names: dict[str, str] = {"#s": "status"}
        expr_values: dict[str, Any] = {
            ":status": status,
            ":progress": progress,
            ":msg": progress_message,
        }

        if output_s3_key is not None:
            update_expr += ", output_s3_key = :output_key"
            expr_values[":output_key"] = output_s3_key

        if error is not None:
            update_expr += ", #err = :error"
            expr_names["#err"] = "error"
            expr_values[":error"] = error

        if delta_e is not None:
            update_expr += ", delta_e = :delta_e"
            expr_values[":delta_e"] = _to_decimal(delta_e)

        if corrections_applied is not None:
            update_expr += ", corrections_applied = :corrections"
            expr_values[":corrections"] = corrections_applied

        if status in ("completed", "failed"):
            update_expr += ", completed_at = :completed_at"
            expr_values[":completed_at"] = datetime.utcnow().isoformat()

        self.table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

    def save_result(self, job_id: str, result: ConversionResult) -> None:
        """変換結果をジョブアイテムに追記する。"""
        self.table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=(
                "SET result_success = :success, "
                "result_original_size = :orig, "
                "result_output_size = :out, "
                "result_delta_e = :de, "
                "result_corrections = :corr, "
                "result_regions_count = :rc"
            ),
            ExpressionAttributeValues={
                ":success": result.success,
                ":orig": result.original_size_bytes,
                ":out": result.output_size_bytes,
                ":de": _to_decimal(result.delta_e),
                ":corr": result.corrections_applied,
                ":rc": len(result.correction_regions),
            },
        )

    def get_job(self, job_id: str) -> ConversionJob | None:
        """ジョブをDynamoDBから取得する。"""
        response = self.table.get_item(Key={"job_id": job_id})
        item = response.get("Item")
        if not item:
            return None
        return self._item_to_job(item)

    def get_result(self, job_id: str) -> ConversionResult | None:
        """変換結果をDynamoDBから取得する。"""
        response = self.table.get_item(Key={"job_id": job_id})
        item = response.get("Item")
        if not item or "result_success" not in item:
            return None
        return ConversionResult(
            job_id=job_id,
            success=bool(item["result_success"]),
            output_path=item.get("output_s3_key"),
            original_size_bytes=int(item.get("result_original_size", 0)),
            output_size_bytes=int(item.get("result_output_size", 0)),
            delta_e=_from_decimal(item.get("result_delta_e")) or 0.0,
            corrections_applied=bool(item.get("result_corrections", False)),
            correction_regions=[
                Region(**r) for r in item.get("result_region_details", [])
            ],
        )

    def _item_to_job(self, item: dict[str, Any]) -> ConversionJob:
        options_raw = item.get("options", {})
        job = ConversionJob(
            job_id=item["job_id"],
            input_file_path=item.get("input_s3_key", ""),
            original_filename=item.get("original_filename", ""),
            options=ConversionOptions(
                target_size_kb=options_raw.get("target_size_kb"),
                quality=int(options_raw.get("quality", 85)),
                max_delta_e=float(options_raw.get("max_delta_e", 2.0)),
            ),
        )
        job.status = item["status"]  # type: ignore[assignment]
        job.progress = int(item.get("progress", 0))
        job.progress_message = item.get("progress_message", "")
        job.output_file_path = item.get("output_s3_key")
        if item.get("completed_at"):
            job.completed_at = datetime.fromisoformat(item["completed_at"])
        job.error = item.get("error")
        job.delta_e = _from_decimal(item.get("delta_e"))
        job.corrections_applied = bool(item.get("corrections_applied", False))
        return job
