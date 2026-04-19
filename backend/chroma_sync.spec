# -*- mode: python ; coding: utf-8 -*-
"""
PyInstallerスペックファイル
macOS (arm64/x64) と Windows (x64) に対応。

ビルド方法:
  macOS:   pyinstaller chroma_sync.spec
  Windows: pyinstaller chroma_sync.spec
"""
import os
import sys
from pathlib import Path

block_cipher = None

# ImageMagickライブラリのパスを検出
def find_imagemagick_libs():
    """プラットフォーム別にImageMagickライブラリを検出する"""
    binaries = []
    if sys.platform == "darwin":
        # Homebrew (Apple Silicon / Intel)
        brew_prefixes = [
            "/opt/homebrew",   # Apple Silicon
            "/usr/local",      # Intel
        ]
        for prefix in brew_prefixes:
            lib_dir = Path(prefix) / "lib"
            if lib_dir.exists():
                for lib in lib_dir.glob("libMagick*.dylib"):
                    binaries.append((str(lib), "."))
                for lib in lib_dir.glob("libgomp*.dylib"):
                    binaries.append((str(lib), "."))
                # ImageMagickのコーデック/モジュール
                for im_dir in lib_dir.glob("ImageMagick-*/modules-Q16HDRI"):
                    binaries.append((str(im_dir), "ImageMagick-modules"))
    elif sys.platform == "win32":
        # Windows: ImageMagick installフォルダ（環境変数 MAGICK_HOME を利用）
        magick_home = os.environ.get("MAGICK_HOME", r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI")
        if Path(magick_home).exists():
            for dll in Path(magick_home).glob("*.dll"):
                binaries.append((str(dll), "."))
            modules = Path(magick_home) / "modules"
            if modules.exists():
                binaries.append((str(modules), "modules"))
    return binaries


a = Analysis(
    ["run_server.py"],
    pathex=["."],
    binaries=find_imagemagick_libs(),
    datas=[
        ("app", "app"),
        ("iccprofiles", "iccprofiles"),
    ],
    hiddenimports=[
        # uvicorn
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.loops.uvloop",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.protocols.websockets.wsproto_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        # fastapi / starlette
        "fastapi",
        "starlette",
        "starlette.routing",
        "starlette.middleware",
        "starlette.middleware.cors",
        "starlette.responses",
        "starlette.staticfiles",
        "starlette.websockets",
        "anyio",
        "anyio._backends._asyncio",
        # 画像処理
        "wand",
        "wand.image",
        "wand.color",
        "wand.drawing",
        "PIL",
        "PIL.Image",
        "PIL.ImageCms",
        "skimage",
        "skimage.color",
        "skimage.color.colorconv",
        "numpy",
        # その他
        "multipart",
        "aiofiles",
        "h11",
        "httptools",
        "websockets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
        "IPython",
        "jupyter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="chroma_sync",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # コンソールウィンドウを非表示
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="chroma_sync",
)
