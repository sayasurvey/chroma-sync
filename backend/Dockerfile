FROM python:3.11-slim

# ImageMagick と依存パッケージのインストール
RUN apt-get update && apt-get install -y \
    imagemagick \
    libmagickwand-dev \
    ghostscript \
    liblcms2-dev \
    libffi-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ImageMagick のポリシーを変更して PDF/AI 処理を許可
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || true
RUN sed -i 's/<policy domain="coder" rights="none" pattern="PS"/<policy domain="coder" rights="read|write" pattern="PS"/' /etc/ImageMagick-6/policy.xml || true

# Poetry のインストール
RUN pip install poetry==1.8.2

WORKDIR /app

# 依存ファイルのコピーとインストール
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# アップロードディレクトリの作成
RUN mkdir -p /app/uploads

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
