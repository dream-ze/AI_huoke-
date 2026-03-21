"""
PyInstaller 打包入口 - 启动 FastAPI 后端服务
"""
import sys
import os

# PyInstaller 打包后，修正模块路径
if getattr(sys, "frozen", False):
    # 运行在 PyInstaller bundle 中
    bundle_dir = sys._MEIPASS
    sys.path.insert(0, bundle_dir)
    # 将工作目录切换到 exe 所在目录，以便读取 .env 文件
    exe_dir = os.path.dirname(sys.executable)
    os.chdir(exe_dir)

import uvicorn

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        # 打包模式下不使用 reload
        reload=False,
    )
