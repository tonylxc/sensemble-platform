import time
from app.ratelimit import check_rate


def test_disabled_always_allows():
    for _ in range(5):
        assert check_rate("k_off", 0.0) is True


def test_blocks_burst():
    assert check_rate("k_burst", 10.0) is True    # 首次放行
    assert check_rate("k_burst", 10.0) is False   # 紧接着被限流


def test_recovers_after_interval():
    assert check_rate("k_rec", 0.05) is True
    time.sleep(0.06)
    assert check_rate("k_rec", 0.05) is True
