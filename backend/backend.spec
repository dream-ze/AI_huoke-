# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包规范
打包命令: pyinstaller backend.spec --clean
"""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["server.py"],
    pathex=[str(Path(".").resolve())],
    binaries=[],
    datas=[
        # 包含 .env 示例文件（如存在）
        (".env.example", "."),
        # AI prompt templates
        ("app/ai/prompts", "app/ai/prompts"),
        # 合规规则（如存在）
        ("app/rules", "app/rules"),
    ],
    hiddenimports=[
        # FastAPI / Starlette
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "fastapi",
        "fastapi.middleware.cors",
        # SQLAlchemy
        "sqlalchemy",
        "sqlalchemy.dialects.postgresql",
        "sqlalchemy.dialects.postgresql.psycopg2",
        "sqlalchemy.orm",
        "sqlalchemy.ext.declarative",
        "sqlalchemy.pool",
        # psycopg2
        "psycopg2",
        "psycopg2.extensions",
        "psycopg2._psycopg",
        # Pydantic
        "pydantic",
        "pydantic_settings",
        "pydantic.v1",
        # jose / cryptography
        "jose",
        "jose.backends",
        "jose.backends.cryptography_backend",
        "cryptography",
        "cryptography.hazmat.bindings._rust",
        # passlib
        "passlib",
        "passlib.handlers",
        "passlib.handlers.bcrypt",
        "passlib.handlers.sha2_crypt",
        "bcrypt",
        # multipart
        "multipart",
        "python_multipart",
        # aiohttp / httpx
        "aiohttp",
        "httpx",
        # python-dotenv
        "dotenv",
        # app modules
        "app",
        "app.api",
        "app.api.endpoints",
        "app.api.v1",
        "app.api.v1.endpoints",
        "app.core",
        "app.models",
        "app.schemas",
        "app.services",
        "app.domains",
        "app.domains.acquisition",
        "app.domains.ai_workbench",
        "app.integrations",
        "app.integrations.ark",
        "app.integrations.ocr",
        "app.integrations.storage",
        "app.integrations.wecom",
        "app.ai",
        "app.ai.agents",
        "app.ai.prompts",
        "app.ai.rag",
        "app.rules",
        "app.repositories",
        "app.tasks",
        "app.utils",
        "app.workers",
        "main",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "PIL",
        "cv2",
        "test",
        "tests",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # 保留控制台窗口便于调试，发布时可改为 False
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
