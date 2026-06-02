# 众感 Sensemble SDK / 接入示例

对接平台开放 API（`/api/v1/open/*`，用 API Key）与设备上报（`/api/v1/data`）。

## Python
```bash
pip install requests
```
```python
from sensemble_sdk import SensembleClient

# A) 第三方用 API Key 取已发布的公开数据集
c = SensembleClient("http://149.248.16.187:8000", api_key="sk_xxx")
for ds in c.list_open_datasets(keyword="温度"):
    print(ds["dataset_id"], ds["name"], ds["dqs"], ds["grade"])
rows = c.download_dataset("SMDP-2026-0001")          # [{ts, metric, value}, ...]

# B) 登录后创建自己的 API Key
c2 = SensembleClient("http://149.248.16.187:8000")
c2.login("teacher1", "pass")
print("我的 Key：", c2.create_api_key("research"))    # 仅显示一次

# C) 设备上报（拿到设备 Token 后）
dev = c2.register_device("esp32-9", type="ESP32", sample_interval=60)
c2.ingest("esp32-9", dev["device_token"], [{"metric": "temperature", "value": 23.5}])
```

## JavaScript（浏览器 / Node 18+）
```js
const base = 'http://149.248.16.187:8000', key = 'sk_xxx'

// 取公开数据集
const list = await (await fetch(`${base}/api/v1/open/datasets`, {
  headers: { 'X-API-Key': key }
})).json()

// 下载某数据集（JSON）
const rows = await (await fetch(`${base}/api/v1/open/datasets/SMDP-2026-0001/download?format=json`, {
  headers: { 'X-API-Key': key }
})).json()
```

## 如何获取 API Key
登录平台 → 调 `POST /api/v1/keys?name=xxx`（带 JWT），返回的 `api_key` 仅显示一次，请保存。
完整接口见运行中的 Swagger：`http://<server>:8000/docs`。
