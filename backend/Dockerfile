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

# ImageMagick のポリシーを変更して PDF/AI/EPS/PS 処理を許可（IM6/IM7 両対応）
RUN for policy_xml in /etc/ImageMagick-6/policy.xml /etc/ImageMagick-7/policy.xml; do \
      [ -f "$policy_xml" ] && sed -i \
        -e 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/g' \
        -e 's/rights="none" pattern="PS"/rights="read|write" pattern="PS"/g' \
        -e 's/rights="none" pattern="EPS"/rights="read|write" pattern="EPS"/g' \
        -e 's/rights="none" pattern="XPS"/rights="read|write" pattern="XPS"/g' \
        "$policy_xml" || true; \
    done

# メモリ制限を引き上げて大きな AI ファイルを処理できるようにする（IM6/IM7 両対応）
RUN for policy_xml in /etc/ImageMagick-6/policy.xml /etc/ImageMagick-7/policy.xml; do \
      [ -f "$policy_xml" ] && sed -i \
        -e 's/<policy domain="resource" name="memory" value="[^"]*"\/>/<policy domain="resource" name="memory" value="2GiB"\/>/' \
        -e 's/<policy domain="resource" name="disk" value="[^"]*"\/>/<policy domain="resource" name="disk" value="4GiB"\/>/' \
        "$policy_xml" || true; \
    done

# Poetry のインストール
RUN pip install poetry==1.8.2

WORKDIR /app

# 依存ファイルのコピーとインストール
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# アップロードディレクトリの作成
RUN mkdir -p /app/uploads /app/iccprofiles

COPY . .

# プロジェクト同梱の ICC プロファイルをシステムに配置
RUN if [ -f /app/iccprofiles/GenericCMYK.icc ]; then \
        cp /app/iccprofiles/GenericCMYK.icc /usr/share/color/icc/GenericCMYK.icc; \
    fi && \
    if [ -f /app/iccprofiles/sRGB.icc ]; then \
        cp /app/iccprofiles/sRGB.icc /usr/share/color/icc/sRGB.icc; \
    fi && \
    if [ -f /app/iccprofiles/DisplayP3.icc ]; then \
        cp /app/iccprofiles/DisplayP3.icc /usr/share/color/icc/DisplayP3.icc; \
    fi

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
