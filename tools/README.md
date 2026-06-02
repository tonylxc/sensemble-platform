# 造数脚本 simulate.py

让平台“活”起来：自动建模拟设备 → 回填历史 → 持续上报。

## 用法
```bash
pip install -r tools/requirements.txt
# 确保后端已起（docker compose up -d）
python tools/simulate.py                      # 3 设备 + 回填48h + live(HTTP, 每5s)
```

常用参数：
| 参数 | 默认 | 说明 |
|---|---|---|
| `--devices N` | 3 | 模拟设备数 |
| `--backfill-hours H` | 48 | 回填过去多少小时 |
| `--interval S` | 300 | 回填采样间隔(秒) |
| `--no-backfill` | - | 跳过回填 |
| `--no-live` | - | 只回填不实时 |
| `--live-interval S` | 5 | 实时上报间隔(秒) |
| `--mqtt` | - | 实时改走 MQTT(`sensemble/{id}/data`) |
| `--api` | http://localhost:8000 | 后端地址 |
| `--db` | postgresql://sensemble:sensemble@localhost:5432/sensemble | 回填直连库 |

## 说明
- **回填**直接写 TimescaleDB（API 的 `/data` 会用服务器时间戳，无法回填历史，故走 DB）。
- **实时**走 API/MQTT，与真实设备路径一致。
- 设备 Token 仅注册时返回一次，已缓存到 `tools/.sim_tokens.json`（勿提交，已在 .gitignore）。
- 跑完用 `sim_teacher / sim123456` 登录前端，或任意账号看「数据集广场」公开集；可视化页选 `sim-esp32-001` 看曲线。
