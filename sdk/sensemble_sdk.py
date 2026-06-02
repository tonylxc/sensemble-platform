"""众感 Sensemble Python SDK（FR-12.2）。依赖：pip install requests

第三方用 API Key 取公开数据：
    from sensemble_sdk import SensembleClient
    c = SensembleClient("http://149.248.16.187:8000", api_key="sk_xxx")
    print(c.list_open_datasets(keyword="温度"))
    rows = c.download_dataset("SMDP-2026-0001")        # [{ts, metric, value}, ...]

登录 + 设备上报：
    c = SensembleClient("http://149.248.16.187:8000")
    c.login("stud1", "pass")
    dev = c.register_device("esp32-9", type="ESP32")   # 含一次性 device_token
    c.ingest("esp32-9", dev["device_token"], [{"metric": "temperature", "value": 23.5}])
"""
import csv
import io
import requests


class SensembleClient:
    def __init__(self, base_url, api_key=None, token=None, timeout=15):
        self.base = base_url.rstrip("/")
        self.api_key = api_key
        self.token = token
        self.timeout = timeout

    def _headers(self, extra=None):
        h = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if self.api_key:
            h["X-API-Key"] = self.api_key
        if extra:
            h.update(extra)
        return h

    # ---------- 用户态 ----------
    def login(self, username, password):
        r = requests.post(f"{self.base}/api/v1/auth/login",
                          data={"username": username, "password": password}, timeout=self.timeout)
        r.raise_for_status()
        self.token = r.json()["access_token"]
        return self.token

    def register_device(self, device_id, **kw):
        r = requests.post(f"{self.base}/api/v1/devices", json={"device_id": device_id, **kw},
                          headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def create_api_key(self, name="sdk"):
        r = requests.post(f"{self.base}/api/v1/keys", params={"name": name},
                          headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.json()["api_key"]

    # ---------- 设备上报 ----------
    def ingest(self, device_id, device_token, points):
        r = requests.post(f"{self.base}/api/v1/data", json=points,
                          headers={"X-Device-Id": device_id, "X-Device-Token": device_token},
                          timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ---------- 开放数据（API Key）----------
    def list_open_datasets(self, keyword=None):
        r = requests.get(f"{self.base}/api/v1/open/datasets",
                         params={"keyword": keyword} if keyword else None,
                         headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def download_dataset(self, dataset_id, fmt="json"):
        r = requests.get(f"{self.base}/api/v1/open/datasets/{dataset_id}/download",
                         params={"format": fmt}, headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        if fmt == "json":
            return r.json()
        return list(csv.DictReader(io.StringIO(r.text)))


if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    key = sys.argv[2] if len(sys.argv) > 2 else None
    c = SensembleClient(base, api_key=key)
    print(c.list_open_datasets())
