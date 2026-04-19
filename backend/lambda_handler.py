"""API Lambda エントリーポイント。

FastAPI アプリを Mangum でラップして Lambda から実行できるようにする。
"""
from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="off")
