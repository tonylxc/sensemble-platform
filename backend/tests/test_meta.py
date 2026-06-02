def test_sensor_types(client):
    r = client.get("/api/v1/meta/sensor-types")
    assert r.status_code == 200
    types = r.json()
    assert isinstance(types, list) and len(types) >= 5
    dht = next((t for t in types if t["model"] == "DHT22"), None)
    assert dht and "temperature" in dht["metrics"]


def test_storage_archive_disabled():
    from app import storage
    from app.config import settings
    old = settings.minio_enabled
    settings.minio_enabled = False
    try:
        assert storage.archive_csv("x.csv", b"a,b\n1,2\n") is None
    finally:
        settings.minio_enabled = old
