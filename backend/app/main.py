import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import convert, health
from app.api.convert import job_queue
from app.config import settings
from app.services.file_manager import FileManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションの起動・終了処理（ローカル開発環境のみ）"""
    if not settings.use_aws:
        os.makedirs(settings.upload_dir, exist_ok=True)
        file_manager = FileManager(settings.upload_dir)
        cleanup_task = asyncio.create_task(_periodic_cleanup(file_manager))

    yield

    if not settings.use_aws:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


async def _periodic_cleanup(file_manager: FileManager) -> None:
    """1時間ごとに期限切れファイルとジョブをメモリから削除する（ローカル開発用）"""
    while True:
        await asyncio.sleep(3600)
        await file_manager.cleanup_expired_files(settings.file_retention_hours)
        job_queue.cleanup_expired_jobs(settings.file_retention_hours)


app = FastAPI(
    title="chroma-sync API",
    description="AI/PSDファイルをJPEGに色味を保持しながら変換するAPI",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(convert.router, prefix="/api", tags=["convert"])
