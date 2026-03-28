from threading import Lock


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
