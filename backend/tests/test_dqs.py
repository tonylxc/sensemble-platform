from app.dqs import compute, grade, completeness, metadata_completeness, anomaly_rate

FULL_META = {"sensor_type": "DHT22", "accuracy": "0.5", "sample_interval": 60,
             "location": "A-301", "calibration_date": "2026-05-30"}


def test_completeness():
    assert completeness(50, 100) == 0.5
    assert completeness(0, 0) == 0.0
    assert completeness(200, 100) == 1.0


def test_metadata_completeness():
    assert metadata_completeness({}) == 0.0
    assert metadata_completeness(FULL_META) == 1.0
    assert metadata_completeness({"sensor_type": "x"}) == 0.2


def test_anomaly_rate_constant_is_zero():
    assert anomaly_rate([23.0] * 50) == 0.0


def test_anomaly_rate_detects_outlier():
    vals = [23.0] * 50 + [9999.0]
    assert anomaly_rate(vals) > 0.0


def test_grade_thresholds():
    assert grade(90) == "A"
    assert grade(75) == "B"
    assert grade(62) == "C"
    assert grade(50) == "D"


def test_compute_high_quality():
    score, g, detail = compute(100, 100, FULL_META, [23.0] * 50)
    assert score == 100.0 and g == "A"
    assert detail["completeness"] == 1.0 and detail["metadata"] == 1.0


def test_compute_low_completeness():
    score, g, _ = compute(5, 1000, {}, [1, 2, 3, 4, 5])
    assert score < 60 and g == "D"


def test_compute_full_5dim():
    import datetime as dt
    from app.dqs import compute_full
    base = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)
    ts = [base + dt.timedelta(seconds=60 * i) for i in range(10)]   # 均匀 60s 间隔
    score, g, d = compute_full(10, 10, FULL_META, [23.0] * 10, ts, 60)
    assert 0 <= score <= 100 and d["version"] == "v2-5dim"
    assert d["continuity"] == 1.0          # 均匀间隔 → 完全连续
    assert d["calibration"] == 1.0         # 有 accuracy + calibration_date
