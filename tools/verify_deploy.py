#!/usr/bin/env python3
"""众感 Sensemble 部署验证（零依赖，仅标准库）：
DNS / HTTP跳转 / HTTPS / 证书 / API链路 / www。

用法:  python tools/verify_deploy.py [domain] [expected_ip]
默认:  domain=sensemble.org  expected_ip=149.248.16.187
③（aaPanel 反代 + Let's Encrypt）完成后应全部 ✓。
"""
import datetime
import http.client
import json
import socket
import ssl
import sys

DOMAIN = sys.argv[1] if len(sys.argv) > 1 else "sensemble.org"
IP = sys.argv[2] if len(sys.argv) > 2 else "149.248.16.187"
m = lambda b: "✓" if b else "✗"


def http_get(host, port, path, https, timeout=12):
    """GET 不跟随跳转；https=True 时校验证书。返回 (status, headers, body) 或 None。"""
    try:
        Conn = http.client.HTTPSConnection if https else http.client.HTTPConnection
        conn = Conn(host, port, timeout=timeout)
        conn.request("GET", path, headers={"User-Agent": "verify"})
        resp = conn.getresponse()
        body = resp.read(200000).decode("utf-8", "ignore")
        hdrs = {k.lower(): v for k, v in resp.getheaders()}
        conn.close()
        return resp.status, hdrs, body
    except Exception:
        return None


print(f"== 众感部署验证 ({DOMAIN}) ==")

# [1] DNS
try:
    addrs = sorted({ai[4][0] for ai in socket.getaddrinfo(DOMAIN, None, socket.AF_INET)})
except Exception:
    addrs = []
print(f"[1] DNS       {m(IP in addrs)}  {DOMAIN} -> {','.join(addrs) or '解析失败'}")

# [2] HTTP -> HTTPS 跳转
res = http_get(DOMAIN, 80, "/", https=False)
code = res[0] if res else 0
loc = res[1].get("location", "") if res else ""
print(f"[2] HTTP跳转  {m(code in (301,302,307,308) and loc.startswith('https'))}  {code} {('-> '+loc[:36]) if loc else ''}")

# [3] HTTPS 页面（成功即证书受信且域名匹配）
res = http_get(DOMAIN, 443, "/", https=True)
page = res[0] if res else 0
body = res[2] if res else ""
app = ("Sensemble" in body or 'id="app"' in body or "id=app" in body)
print(f"[3] HTTPS页面 {m(page==200)}  {page}  {'(众感前端)' if app else ''}")

# [4] 证书信息（颁发者 / 到期）
try:
    ctx = ssl.create_default_context()
    with socket.create_connection((DOMAIN, 443), timeout=12) as sk:
        with ctx.wrap_socket(sk, server_hostname=DOMAIN) as ss:
            c = ss.getpeercert()
    issuer = dict(x[0] for x in c["issuer"]).get("organizationName", "?")
    exp = datetime.datetime.strptime(c["notAfter"], "%b %d %H:%M:%S %Y %Z")
    days = (exp - datetime.datetime.utcnow()).days
    print(f"[4] 证书      {m(days>0)}  颁发者={issuer}  到期={exp:%Y-%m-%d}（剩 {days} 天）")
except Exception as e:
    print(f"[4] 证书      ✗  抓取失败（③未完成？{type(e).__name__}）")

# [5] API 链路（经反代→前端→/api→后端；公开端点 sensor-types）
res = http_get(DOMAIN, 443, "/api/v1/meta/sensor-types", https=True)
n = 0
if res and res[0] == 200:
    try:
        n = len(json.loads(res[2]))
    except Exception:
        n = 0
print(f"[5] API链路   {m(n>0)}  /api/v1/meta/sensor-types  ({n} 型号)")

# [6] www
res = http_get("www." + DOMAIN, 443, "/", https=True)
w = res[0] if res else 0
print(f"[6] www       {m(w==200)}  -> {w}")

print("\n③完成后应全部 ✓。当前内测期 [2]~[6] 为 ✗ 属正常（HTTPS 尚未配）。")
