from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check() -> JSONResponse:
    """ヘルスチェックエンドポイント"""
    return JSONResponse({"status": "ok", "service": "chroma-sync"})
