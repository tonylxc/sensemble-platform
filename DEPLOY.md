# 部署到云服务器（Ubuntu 22.04）

服务器：`149.248.16.187`（Label: Sensemble-web-data-server，4GB/80GB，LA）

---

## ⚠️ 第 0 步：先改 root 密码（重要）
你的 root 密码已在对话中明文出现 = **已暴露**，请立刻改：
```bash
ssh root@149.248.16.187      # 输入当前密码
passwd                       # 设置一个新密码
```
> 强烈建议随后改成「SSH 密钥登录 + 禁用密码」，见文末「安全加固」。

## 第 1 步：上传代码（在你的 Windows PowerShell 里）
Windows 10/11 自带 scp：
```powershell
scp D:\BaiduSyncdisk\sensemble-platform.tar.gz root@149.248.16.187:/root/
```

## 第 2 步：在服务器上一键部署
```bash
ssh root@149.248.16.187
mkdir -p /opt && tar -xzf /root/sensemble-platform.tar.gz -C /opt
cd /opt/sensemble-platform
bash deploy.sh                                # 装 Docker → 生成密钥 → 起全栈
```
脚本结尾会打印**访问地址**和**管理员密码**（也可 `cat /opt/sensemble-platform/.env` 查看）。

## 第 3 步：访问
- 前端：`http://149.248.16.187/`
- API / Swagger：`http://149.248.16.187:8000/docs`
- 设备 MQTT：`149.248.16.187:1883`（username=设备ID，password=设备Token）

## 第 4 步（可选）：灌演示数据，让图表“活”起来
```bash
cd /opt/sensemble-platform
apt-get install -y python3-pip
pip3 install -r tools/requirements.txt
python3 tools/simulate.py            # 建 3 设备 + 回填 48h + 实时上报
```
然后前端用 `sim_teacher / sim123456` 登录 → 数据可视化 → 看活曲线 + IDW 热力图。

---

## 常用运维
```bash
cd /opt/sensemble-platform
docker compose -f docker-compose.prod.yml ps                 # 看状态
docker compose -f docker-compose.prod.yml logs -f backend    # 看后端日志
docker compose -f docker-compose.prod.yml restart backend    # 重启某服务
docker compose -f docker-compose.prod.yml up -d --build      # 改代码后重新部署
docker compose -f docker-compose.prod.yml down               # 停（数据卷保留）
```

## 安全加固（建议）
- **改 root 密码**（见第 0 步）。
- **SSH 密钥登录**：本机 `ssh-keygen -t ed25519`；上传公钥：
  ```powershell
  type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@149.248.16.187 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
  ```
  服务器 `/etc/ssh/sshd_config` 设 `PasswordAuthentication no`，再 `systemctl restart ssh`。
- DB / MinIO / EMQX 仪表盘已只绑 `127.0.0.1`，需要访问就开 SSH 隧道，例如看 EMQX 仪表盘：
  ```bash
  ssh -L 18083:localhost:18083 root@149.248.16.187   # 然后本机浏览器开 http://localhost:18083
  ```
- 不想公网直连 API，把 `docker-compose.prod.yml` 里 backend 的 `"8000:8000"` 改成 `"127.0.0.1:8000:8000"`（前端仍通过 nginx 的 /api 正常工作）。
- **上 HTTPS**：需要一个域名解析到 `149.248.16.187`，再加 Caddy / nginx + Let's Encrypt 自动证书。要做的话告诉我，我给你加一个 Caddy 反代（一文件搞定，自动续签）。

## 排错
- `docker compose ... logs backend`：后端起不来通常是 .env / DB 未就绪，稍等重试。
- 首次 EMQX 可能因后端未完全就绪有几条认证失败日志，自动重连后恢复，属正常。
- 4GB 内存构建前端较慢但够用；若 OOM，可先 `docker compose ... build frontend` 单独构建。
