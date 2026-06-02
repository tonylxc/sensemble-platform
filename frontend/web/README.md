# 众感 Sensemble — Web 前端

Vue 3 + Vite + Pinia + vue-router + axios + ECharts。对接后端 FastAPI 骨架（`../../backend`）。

## 运行
```bash
# 1) 先起后端（在仓库根目录）
docker compose up -d --build        # 后端在 http://localhost:8000

# 2) 起前端
cd frontend/web
cp .env.example .env                # 可留空，走 Vite 代理
npm install
npm run dev                         # http://localhost:5173
```
> 默认管理员 `admin / admin123`（后端 .env）。也可在登录页直接注册学生/教师账号。

## 体验闭环
1. 注册/登录 → 2. 「我的设备」注册设备（拿到一次性 Token）→ 3. 用「灌测试数据」按钮造几条数据 →
4. 「数据可视化」选设备/指标看 ECharts 折线 → 5. 在可视化页「打包为数据集」(自动算 DQS) →
6. 「数据集广场」找到草稿点「提交审核」→ 7. 切教师账号在「审核队列」通过 → 8. 回到广场可下载 CSV。

## 结构
```
src/
├─ main.js  App.vue
├─ api/        client.js(axios+拦截器)  index.js(各接口)
├─ stores/     auth.js (Pinia: token/role/登录态)
├─ router/     index.js (路由+鉴权守卫)
├─ components/  AppLayout.vue(侧栏+顶栏)  LineChart.vue(ECharts封装)
├─ views/       Login Overview Devices Visualize Datasets Review
└─ styles/      main.css (众感 v2 配色)
```
配色：青 #0E8C82 / 紫 #7C3AED / 品红 #DB2777（与品牌 v2 一致）。
