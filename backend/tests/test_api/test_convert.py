import io

import pytest


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

    def test_get_nonexistent_job_status(self, client):
        """存在しないジョブIDで404エラー"""
        response = client.get("/api/convert/nonexistent-job-id/status")
        assert response.status_code == 404

    def test_get_nonexistent_job_result(self, client):
        """存在しないジョブIDで404エラー"""
        response = client.get("/api/convert/nonexistent-job-id/result")
        assert response.status_code == 404
