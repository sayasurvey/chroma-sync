import io
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.job import ConversionJob, ConversionOptions
from app.models.result import ConversionResult


class TestHealthEndpoint:
    def test_health_check(self, client):
        """ヘルスチェックエンドポイントが200を返す"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestConvertEndpoint:
    def test_upload_invalid_format(self, client):
        """非対応ファイル形式のアップロードで422エラー"""
        file_content = b"dummy text content"
        response = client.post(
            "/api/convert",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert response.status_code == 422

    def test_upload_png_invalid(self, client):
        """PNGファイルは非対応形式のため422エラー"""
        file_content = b"\x89PNG\r\n\x1a\n"  # PNGマジックバイト
        response = client.post(
            "/api/convert",
            files={"file": ("test.png", io.BytesIO(file_content), "image/png")},
        )
        assert response.status_code == 422

    def test_upload_valid_ai_file_creates_job(self, client):
        """有効な拡張子のファイルをアップロードするとジョブが作成される"""
        file_content = b"%PDF-1.4 dummy ai content"
        mock_job = ConversionJob(
            job_id="test-job-id",
            input_file_path="/tmp/test.ai",
            original_filename="test.ai",
            options=ConversionOptions(),
            status="pending",
        )

        with (
            patch("app.api.convert.file_manager.save_upload", new_callable=AsyncMock, return_value="/tmp/test.ai"),
            patch("app.api.convert.job_queue.enqueue", new_callable=AsyncMock, return_value=mock_job),
        ):
            response = client.post(
                "/api/convert",
                files={"file": ("test.ai", io.BytesIO(file_content), "application/postscript")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-job-id"
        assert data["status"] == "pending"

    def test_get_nonexistent_job_status(self, client):
        """存在しないジョブIDで404エラー"""
        response = client.get("/api/convert/nonexistent-job-id/status")
        assert response.status_code == 404

    def test_get_nonexistent_job_result(self, client):
        """存在しないジョブIDで404エラー"""
        response = client.get("/api/convert/nonexistent-job-id/result")
        assert response.status_code == 404


class TestJobStatusEndpoint:
    def _make_job(self, status: str = "pending", **kwargs) -> ConversionJob:
        return ConversionJob(
            job_id="test-job-id",
            input_file_path="/tmp/test.ai",
            original_filename="test.ai",
            options=ConversionOptions(),
            status=status,
            created_at=datetime.utcnow(),
            **kwargs,
        )

    def test_get_pending_job_status(self, client):
        """pending状態のジョブステータスが正しく返る"""
        mock_job = self._make_job("pending")

        with patch("app.api.convert.job_queue.get_job", return_value=mock_job):
            response = client.get("/api/convert/test-job-id/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["job_id"] == "test-job-id"
        assert "created_at" in data

    def test_get_failed_job_status_includes_error(self, client):
        """failed状態のジョブステータスにエラーメッセージが含まれる"""
        mock_job = self._make_job(
            "failed",
            completed_at=datetime.utcnow(),
            error="変換中にエラーが発生しました。",
        )

        with patch("app.api.convert.job_queue.get_job", return_value=mock_job):
            response = client.get("/api/convert/test-job-id/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "変換中にエラーが発生しました。"
        assert "completed_at" in data

    def test_get_completed_job_status_includes_delta_e(self, client):
        """completed状態のジョブステータスにΔEが含まれる"""
        mock_job = self._make_job(
            "completed",
            completed_at=datetime.utcnow(),
            delta_e=1.5,
        )

        with patch("app.api.convert.job_queue.get_job", return_value=mock_job):
            response = client.get("/api/convert/test-job-id/status")

        assert response.status_code == 200
        data = response.json()
        assert data["delta_e"] == 1.5

    def test_get_result_when_not_completed_returns_400(self, client):
        """処理中のジョブの結果取得で400エラー"""
        mock_job = self._make_job("processing")

        with patch("app.api.convert.job_queue.get_job", return_value=mock_job):
            response = client.get("/api/convert/test-job-id/result")

        assert response.status_code == 400

    def test_get_completed_job_result(self, client):
        """完了済みジョブの結果詳細が正しく返る"""
        mock_job = self._make_job(
            "completed",
            completed_at=datetime.utcnow(),
            output_file_path="/tmp/output.jpg",
            delta_e=1.2,
            corrections_applied=True,
        )
        mock_result = ConversionResult(
            job_id="test-job-id",
            success=True,
            output_path="/tmp/output.jpg",
            original_size_bytes=2048,
            output_size_bytes=512,
            delta_e=1.2,
            corrections_applied=True,
        )

        with (
            patch("app.api.convert.job_queue.get_job", return_value=mock_job),
            patch("app.api.convert.job_queue.get_result", return_value=mock_result),
        ):
            response = client.get("/api/convert/test-job-id/result")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["delta_e"] == 1.2
        assert data["corrections_applied"] is True
        assert data["original_size_bytes"] == 2048
        assert data["output_size_bytes"] == 512
        assert data["correction_regions_count"] == 0
