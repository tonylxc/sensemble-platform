"""每设备上报限流（FR-3.4）。内存级最小间隔，0 = 不限流。"""
import time

_last: dict[str, float] = {}


def check_rate(key: str, min_interval: float) -> bool:
    """允许返回 True；过于频繁返回 False。"""
    if min_interval <= 0:
        return True
    now = time.monotonic()
    if now - _last.get(key, 0.0) < min_interval:
        return False
    _last[key] = now
    return True
