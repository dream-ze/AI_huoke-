"""结构化日志配置"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional


class JSONFormatter(logging.Formatter):
    """JSON 格式日志输出"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加请求 ID（如果存在）
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # 添加异常信息
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class RequestIDFilter(logging.Filter):
    """将请求 ID 注入到日志记录中"""

    _request_id: Optional[str] = None

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", self._request_id or "-")
        return True

    @classmethod
    def set_request_id(cls, request_id: Optional[str]):
        """设置当前请求 ID"""
        cls._request_id = request_id

    @classmethod
    def clear_request_id(cls):
        """清除当前请求 ID"""
        cls._request_id = None


def setup_logging(log_level: str = "INFO", json_format: bool = True):
    """配置应用日志

    Args:
        log_level: 日志级别，如 INFO、DEBUG、WARNING
        json_format: 是否使用 JSON 格式输出
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 清除现有 handler
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(request_id)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )

    handler.addFilter(RequestIDFilter())
    root_logger.addHandler(handler)

    # 降低第三方库日志级别
    for noisy_logger in ["uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
