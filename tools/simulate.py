#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""众感 Sensemble 数据模拟器 / 造数脚本。

1) 通过 REST API 创建模拟用户与若干设备（领取一机一 Token，缓存到 .sim_tokens.json）；
2) backfill：直连 TimescaleDB，回填过去 N 小时历史数据（让图表立刻有曲线）；
3) live：循环通过 HTTP（默认）或 MQTT 持续上报，让图表“活”起来。

依赖：pip install -r tools/requirements.txt
示例：
  python tools/simulate.py                         # 3 设备 + 回填 48h + 进入 live(HTTP)
  python tools/simulate.py --devices 5 --backfill-hours 168 --no-live
  python tools/simulate.py --no-backfill --mqtt    # 仅 live，走 MQTT
"""
import argparse
import json
import math
import os
import random
import time
import datetime as dt

import requests

TOKEN_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".sim_tokens.json")
METRICS = ["temperature", "humidity", "co2"]
CAMPUS = (30.7600, 120.7500)  # 模拟校园中心（可改）


def gen(metric, when):
    """按一天周期 + 噪声生成拟真值。"""
    h = when.hour + when.minute / 60.0
    if metric == "temperature":
        return round(23 + 3 * math.sin((h - 9) / 24 * 2 * math.pi) + random.gauss(0, 0.4), 2)
    if metric == "humidity":
        return round(min(95, max(20, 50 - 8 * math.sin((h - 9) / 24 * 2 * math.pi) + random.gauss(0, 1.5))), 2)
    if metric == "co2":
        occ = 1.0 if 8 <= h <= 20 else 0.2  # 上课时段更高
        return round(450 + 350 * occ * (0.6 + 0.4 * math.sin((h - 8) / 12 * math.pi)) + random.gauss(0, 30), 1)
    return round(random.gauss(0, 1), 2)


def load_cache():
    try:
        return json.load(open(TOKEN_CACHE, encoding="utf-8"))
    except Exception:
        return {}


def save_cache(c):
    json.dump(c, open(TOKEN_CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def ensure_user(api, user, pw):
    try:
        requests.post(f"{api}/api/v1/auth/register",
                      json={"username": user, "password": pw, "role": "teacher"}, timeout=10)
    except Exception:
        pass
    r = requests.post(f"{api}/api/v1/auth/login", data={"username": user, "password": pw}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def ensure_devices(api, jwt, n, cache):
    headers = {"Authorization": f"Bearer {jwt}"}
    devices = []
    for i in range(1, n + 1):
        did = f"sim-esp32-{i:03d}"
        lat = CAMPUS[0] + (i - 1) * 0.0009
        lon = CAMPUS[1] + ((i - 1) % 3) * 0.0011
        body = {"device_id": did, "type": "ESP32", "location": f"模拟点位-{i}",
                "lat": lat, "lon": lon, "sample_interval": 300,
                "sensors": {"DHT22": {"accuracy": 0.5}, "MH-Z19": {"accuracy": 50}}}
        r = requests.post(f"{api}/api/v1/devices", json=body, headers=headers, timeout=10)
        if r.status_code == 200:
            cache[did] = r.json()["device_token"]
            print(f"  + 注册设备 {did}")
        elif did in cache:
            print(f"  · 设备 {did} 已存在，复用缓存 Token")
        else:
            print(f"  ! 设备 {did} 已存在但无缓存 Token（live 将跳过；删除该设备或清 .sim_tokens.json 重来）")
        devices.append({"device_id": did, "lat": lat, "lon": lon, "token": cache.get(did)})
    save_cache(cache)
    return devices


def backfill(db_url, devices, hours, interval):
    import psycopg2
    from psycopg2.extras import execute_values, Json
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(hours=hours)
    steps = int(hours * 3600 / interval)
    total = 0
    for d in devices:
        rows = []
        for s in range(steps + 1):
            when = start + dt.timedelta(seconds=s * interval)
            for m in METRICS:
                rows.append((d["device_id"], when, when, m, gen(m, when),
                             d["lat"], d["lon"], Json({"metric": m, "sim": True})))
        execute_values(cur,
            "INSERT INTO sensor_data (device_id, ts, device_ts, metric, value, lat, lon, raw) VALUES %s", rows)
        cur.execute("UPDATE devices SET last_seen=%s WHERE device_id=%s", (now, d["device_id"]))
        total += len(rows)
        print(f"  ↺ 回填 {d['device_id']}: {len(rows)} 行")
    conn.commit()
    cur.close()
    conn.close()
    print(f"回填完成，共 {total} 行（过去 {hours}h / 每 {interval}s 一组）")


def live_http(api, devices, interval):
    while True:
        now = dt.datetime.now(dt.timezone.utc)
        active = [d for d in devices if d["token"]]
        for d in active:
            pts = [{"metric": m, "value": gen(m, now), "device_ts": now.isoformat(),
                    "lat": d["lat"], "lon": d["lon"]} for m in METRICS]
            try:
                requests.post(f"{api}/api/v1/data", json=pts,
                              headers={"X-Device-Id": d["device_id"], "X-Device-Token": d["token"]}, timeout=10)
            except Exception as e:
                print("  ! 上报失败", d["device_id"], e)
        print(f"  ♥ {now.strftime('%H:%M:%S')} HTTP 上报 {len(active)} 设备 × {len(METRICS)} 指标")
        time.sleep(interval)


def live_mqtt(host, port, devices, interval):
    import paho.mqtt.client as mqtt
    # 一机一 Token：每个设备一条连接，username=device_id / password=Token，由 EMQX 认证
    clients = {}
    for d in devices:
        if not d["token"]:
            continue
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=d["device_id"])
        c.username_pw_set(d["device_id"], d["token"])
        try:
            c.connect(host, port, 60)
            c.loop_start()
            clients[d["device_id"]] = c
        except Exception as e:
            print("  ! MQTT 连接失败", d["device_id"], e)
    while True:
        now = dt.datetime.now(dt.timezone.utc)
        for d in devices:
            c = clients.get(d["device_id"])
            if not c:
                continue
            payload = {"data": [{"metric": m, "value": gen(m, now)} for m in METRICS]}  # 无需带 token，EMQX 已认证
            c.publish(f"sensemble/{d['device_id']}/data", json.dumps(payload))
        print(f"  ♥ {now.strftime('%H:%M:%S')} MQTT 发布 {len(clients)} 设备")
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description="众感 Sensemble 造数脚本")
    ap.add_argument("--api", default=os.getenv("SIM_API", "http://localhost:8000"))
    ap.add_argument("--db", default=os.getenv("SIM_DB", "postgresql://sensemble:sensemble@localhost:5432/sensemble"))
    ap.add_argument("--user", default="sim_teacher")
    ap.add_argument("--password", default="sim123456")
    ap.add_argument("--devices", type=int, default=3)
    ap.add_argument("--backfill-hours", type=int, default=48)
    ap.add_argument("--interval", type=int, default=300, help="回填采样间隔(秒)")
    ap.add_argument("--no-backfill", action="store_true")
    ap.add_argument("--no-live", action="store_true")
    ap.add_argument("--live-interval", type=int, default=5)
    ap.add_argument("--mqtt", action="store_true", help="live 走 MQTT 而非 HTTP")
    ap.add_argument("--mqtt-host", default="localhost")
    ap.add_argument("--mqtt-port", type=int, default=1883)
    args = ap.parse_args()

    print(f"API = {args.api}")
    cache = load_cache()
    print("登录 / 创建用户…")
    jwt = ensure_user(args.api, args.user, args.password)
    print("创建 / 复用设备…")
    devices = ensure_devices(args.api, jwt, args.devices, cache)

    if not args.no_backfill:
        print("回填历史数据（直连 TimescaleDB）…")
        try:
            backfill(args.db, devices, args.backfill_hours, args.interval)
        except Exception as e:
            print("回填失败（检查 --db 连接 / 5432 端口是否映射）:", e)

    if not args.no_live:
        print(f"进入 live（{'MQTT' if args.mqtt else 'HTTP'}，每 {args.live_interval}s）… Ctrl+C 退出")
        try:
            if args.mqtt:
                live_mqtt(args.mqtt_host, args.mqtt_port, devices, args.live_interval)
            else:
                live_http(args.api, devices, args.live_interval)
        except KeyboardInterrupt:
            print("\n已停止。")


if __name__ == "__main__":
    main()
