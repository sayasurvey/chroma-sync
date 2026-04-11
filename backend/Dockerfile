FROM python:3.11-slim

# ImageMagick と依存パッケージのインストール
RUN apt-get update && apt-get install -y \
    imagemagick \
    libmagickwand-dev \
    ghostscript \
    liblcms2-dev \
    libffi-dev \
    gcc \
    icc-profiles-free \
    && rm -rf /var/lib/apt/lists/*

# ImageMagick のポリシーを変更して PDF/AI/EPS/PS 処理を許可
RUN sed -i \
    -e 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/g' \
    -e 's/rights="none" pattern="PS"/rights="read|write" pattern="PS"/g' \
    -e 's/rights="none" pattern="EPS"/rights="read|write" pattern="EPS"/g' \
    -e 's/rights="none" pattern="XPS"/rights="read|write" pattern="XPS"/g' \
    /etc/ImageMagick-6/policy.xml || true

# メモリ制限を引き上げて大きな AI ファイルを処理できるようにする
RUN sed -i \
    -e 's/<policy domain="resource" name="memory" value="[^"]*"\/>/<policy domain="resource" name="memory" value="2GiB"\/>/' \
    -e 's/<policy domain="resource" name="disk" value="[^"]*"\/>/<policy domain="resource" name="disk" value="4GiB"\/>/' \
    /etc/ImageMagick-6/policy.xml || true

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
