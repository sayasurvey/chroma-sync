import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import convert, health
from app.config import settings
from app.services.file_manager import FileManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションの起動・終了処理"""
    # アップロードディレクトリの作成
    os.makedirs(settings.upload_dir, exist_ok=True)

    # 期限切れファイルの定期削除タスクを開始
    file_manager = FileManager(settings.upload_dir)
    cleanup_task = asyncio.create_task(_periodic_cleanup(file_manager))

    yield

    # 終了時にクリーンアップタスクを停止
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


async def _periodic_cleanup(file_manager: FileManager) -> None:
    """24時間ごとに期限切れファイルを削除する"""
    while True:
        await asyncio.sleep(3600)  # 1時間ごとにチェック
        await file_manager.cleanup_expired_files(settings.file_retention_hours)


app = FastAPI(
    title="chroma-sync API",
    description="AI/PSDファイルをJPEGに色味を保持しながら変換するAPI",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(convert.router, prefix="/api", tags=["convert"])
