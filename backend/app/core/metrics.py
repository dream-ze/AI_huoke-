import logging
import time
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)

# ========== 原有用户序列指标 ==========
_user_sequence_repair_attempt_total = 0
_user_sequence_repair_success_total = 0
_user_sequence_repair_failure_total = 0
_user_sequence_startup_align_total = 0

_lock = Lock()


def inc_user_sequence_repair_attempt() -> None:
    global _user_sequence_repair_attempt_total
    with _lock:
        _user_sequence_repair_attempt_total += 1


def inc_user_sequence_repair_success() -> None:
    global _user_sequence_repair_success_total
    with _lock:
        _user_sequence_repair_success_total += 1


def inc_user_sequence_repair_failure() -> None:
    global _user_sequence_repair_failure_total
    with _lock:
        _user_sequence_repair_failure_total += 1


def inc_user_sequence_startup_align() -> None:
    global _user_sequence_startup_align_total
    with _lock:
        _user_sequence_startup_align_total += 1


def get_user_sequence_metrics_snapshot() -> dict:
    with _lock:
        return {
            "user_sequence_repair_attempt_total": _user_sequence_repair_attempt_total,
            "user_sequence_repair_success_total": _user_sequence_repair_success_total,
            "user_sequence_repair_failure_total": _user_sequence_repair_failure_total,
            "user_sequence_startup_align_total": _user_sequence_startup_align_total,
        }


# ========== 新增应用业务指标 ==========


class AppMetrics:
    """应用级业务指标收集器"""

    def __init__(self):
        self._counters = {}
        self._histograms = {}
        self._gauges = {}
        self._lock = Lock()

    def increment(self, name: str, value: int = 1, labels: dict = None):
        """递增计数器"""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: dict = None):
        """设置仪表值"""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe_histogram(self, name: str, value: float, labels: dict = None):
        """记录直方图观测值"""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            # 保持最近1000个观测值
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]

    def _make_key(self, name: str, labels: dict = None) -> str:
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name

    def get_metrics_text(self) -> str:
        """导出Prometheus格式文本"""
        lines = []
        with self._lock:
            # 计数器
            for key, value in self._counters.items():
                lines.append(f"zhk_{key} {value}")
            # 仪表
            for key, value in self._gauges.items():
                lines.append(f"zhk_{key} {value}")
            # 直方图
            for key, values in self._histograms.items():
                if values:
                    avg = sum(values) / len(values)
                    sorted_values = sorted(values)
                    p95 = sorted_values[int(len(values) * 0.95)] if len(values) > 1 else values[0]
                    lines.append(f"zhk_{key}_avg {avg:.2f}")
                    lines.append(f"zhk_{key}_p95 {p95:.2f}")
                    lines.append(f"zhk_{key}_count {len(values)}")
        return "\n".join(lines)

    def get_all_metrics(self) -> dict:
        """获取所有指标的字典形式"""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: list(v) for k, v in self._histograms.items()},
            }


# 全局实例
app_metrics = AppMetrics()

# 预定义指标名称常量
METRIC_LOGIN_COUNT = "login_total"
METRIC_GENERATION_COUNT = "generation_total"
METRIC_COMPLIANCE_PASS_COUNT = "compliance_pass_total"
METRIC_COMPLIANCE_FAIL_COUNT = "compliance_fail_total"
METRIC_API_LATENCY = "api_latency_ms"
METRIC_LLM_CALL_COUNT = "llm_call_total"
METRIC_LLM_TOKEN_USED = "llm_tokens_total"
METRIC_RATE_LIMIT_HIT = "rate_limit_hit_total"


def track_latency(metric_name: str):
    """装饰器：追踪函数执行延迟"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start) * 1000
                app_metrics.observe_histogram(metric_name, duration_ms)

        return wrapper

    return decorator


def track_latency_async(metric_name: str):
    """装饰器：追踪异步函数执行延迟"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start) * 1000
                app_metrics.observe_histogram(metric_name, duration_ms)

        return wrapper

    return decorator
