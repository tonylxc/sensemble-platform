#!/usr/bin/env python3
"""众感 Sensemble · STM32 串口 → 平台 网关（零硬件成本上报路径）

复用现有《电气测试技术课程设计》实验装置：STM32 经 USB 串口逐行输出 `指标,数值`
（如 `current,0.83`），本脚本读取后按平台 JSON 批量上报到 /api/v1/data。
学生专注传感器与测量，数据照样进平台看可视化 / 打数据集，不加任何联网硬件。

安装:  pip install pyserial requests
示例:
  python pc_gateway.py --base http://149.248.16.187:8080 \
         --device-id stm32-01 --token <设备Token> --port COM3
无硬件演示(合成读数):        python pc_gateway.py --device-id d1 --token t --demo
只自检不上报(打印 JSON):     python pc_gateway.py --device-id d1 --token t --demo --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from datetime import datetime, timezone


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_line(line: str):
    """解析一行 `metric,value`，返回 {metric,value,device_ts} 或 None（忽略空行/注释/非法行）。"""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = line.split(",")
    if len(parts) < 2 or not parts[0].strip():
        return None
    try:
        value = float(parts[1])
    except ValueError:
        return None
    return {"metric": parts[0].strip(), "value": value, "device_ts": iso_now()}


def demo_lines():
    """无硬件时合成读数：电流(正弦整流)、光照(噪声)、温度(缓变)。"""
    t = 0.0
    while True:
        t += 1.0
        yield f"current,{abs(2.0 * math.sin(t / 6)) + random.uniform(-0.05, 0.05):.3f}"
        yield f"light,{500 + 200 * math.sin(t / 20) + random.uniform(-20, 20):.0f}"
        yield f"temperature,{24 + 2 * math.sin(t / 50) + random.uniform(-0.2, 0.2):.2f}"
        time.sleep(1.0)


def serial_lines(port: str, baud: int):
    import serial  # 延迟导入：仅真实串口时才需要 pyserial
    ser = serial.Serial(port, baud, timeout=1)
    print(f"[串口] 已打开 {port} @ {baud}", flush=True)
    try:
        while True:
            raw = ser.readline()
            if raw:
                yield raw.decode("utf-8", "ignore")
    finally:
        ser.close()


def post(base: str, device_id: str, token: str, points: list, dry_run: bool) -> bool:
    if dry_run:
        print(f"[DRY-RUN] POST {base}/api/v1/data  x{len(points)}: "
              f"{json.dumps(points, ensure_ascii=False)}", flush=True)
        return True
    import requests  # 延迟导入：仅真实上报时才需要 requests
    try:
        r = requests.post(f"{base}/api/v1/data", json=points, timeout=8,
                          headers={"X-Device-Id": device_id, "X-Device-Token": token})
        if r.status_code == 200:
            print(f"[上报] {len(points)} 点 OK", flush=True)
            return True
        if r.status_code == 429:
            print("[上报] 429 限流：加大 --interval", flush=True)
        else:
            print(f"[上报] 失败 {r.status_code}: {r.text[:120]}", flush=True)
        return False
    except Exception as e:
        print(f"[上报] 网络异常: {e}", flush=True)
        return False


def main():
    ap = argparse.ArgumentParser(description="众感 Sensemble STM32 串口网关")
    ap.add_argument("--base", default="http://149.248.16.187:8080", help="平台地址")
    ap.add_argument("--device-id", required=True)
    ap.add_argument("--token", required=True, help="设备 Token（注册设备时一次性返回）")
    ap.add_argument("--port", help="串口号，如 COM3 / /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--interval", type=float, default=2.0, help="上报间隔秒（≥平台限流间隔，默认 2s）")
    ap.add_argument("--demo", action="store_true", help="无硬件，合成读数")
    ap.add_argument("--dry-run", action="store_true", help="只打印不上报（自检）")
    ap.add_argument("--seconds", type=float, default=0, help="运行 N 秒后退出（0=一直）")
    args = ap.parse_args()

    if not args.demo and not args.port:
        ap.error("需要 --port（或用 --demo 无硬件演示）")

    src = demo_lines() if args.demo else serial_lines(args.port, args.baud)
    print(f"[启动] 设备 {args.device_id} → {args.base} | "
          f"{'演示模式' if args.demo else args.port} | 每 {args.interval}s 上报", flush=True)

    buf, last_flush, t0 = [], time.time(), time.time()
    try:
        for line in src:
            pt = parse_line(line)
            if pt:
                buf.append(pt)
            now = time.time()
            if buf and now - last_flush >= args.interval:
                post(args.base, args.device_id, args.token, buf, args.dry_run)
                buf, last_flush = [], now
            if args.seconds and now - t0 >= args.seconds:
                break
    except KeyboardInterrupt:
        print("\n[退出] 收到 Ctrl-C", flush=True)
    if buf:
        post(args.base, args.device_id, args.token, buf, args.dry_run)


if __name__ == "__main__":
    main()
