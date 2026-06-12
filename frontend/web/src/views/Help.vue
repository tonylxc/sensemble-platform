<script setup>
import { computed } from 'vue'
import { toast } from '../toast'

const base = location.origin
const host = location.hostname

// 代码示例放 script 里拼，避免模板里 {{ }} 与 JSON 花括号打架
const curlExample = computed(() => `curl -X POST ${base}/api/v1/data \\
  -H "X-Device-Id: 你的设备ID" \\
  -H "X-Device-Token: 你的Token" \\
  -H "Content-Type: application/json" \\
  -d '[{"metric":"temperature","value":23.5}]'`)

const pyExample = computed(() => `import requests, time, random

BASE = "${base}"
HEADERS = {"X-Device-Id": "你的设备ID", "X-Device-Token": "你的Token"}

while True:
    points = [{"metric": "temperature", "value": round(23 + random.uniform(-1, 1), 2)}]
    r = requests.post(BASE + "/api/v1/data", json=points, headers=HEADERS, timeout=10)
    print(r.status_code, r.text)   # 200=成功 401=ID/Token错 429=太频繁
    time.sleep(2)                  # 上报间隔 ≥1 秒（平台限流）`)

const mqttExample = computed(() => `服务器: ${host}   端口: 1883
主题:   sensemble/你的设备ID/data
报文(JSON):
{"token": "你的Token",
 "data": [{"metric": "temperature", "value": 23.5},
          {"metric": "humidity", "value": 45.2}]}`)

const gatewayExample = `pip install pyserial requests
python pc_gateway.py --base ${base} \\
       --device-id 你的设备ID --token 你的Token --port COM3`

const sdkExample = computed(() => `from sensemble_sdk import SensembleClient
c = SensembleClient("${base}")
c.login("你的用户名", "你的密码")
dev = c.register_device("my-dev-01", type="ESP32")   # 返回一次性 device_token
c.ingest("my-dev-01", dev["device_token"], [{"metric": "temperature", "value": 23.5}])`)

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text)
    toast('已复制')
  } catch (e) {
    // HTTP 环境无 clipboard API：退回 execCommand
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    toast(ok ? '已复制' : '复制失败，请手动选择文本')
  }
}
</script>

<template>
  <div class="card">
    <h3>三步把数据传上平台</h3>
    <div class="steps">
      <div class="step"><span class="n">1</span><b>注册设备</b><span class="muted small">「我的设备」→「+ 注册设备」，记下 设备ID 与一次性 Token</span></div>
      <div class="step"><span class="n">2</span><b>上报数据</b><span class="muted small">下面四条路径任选其一（HTTP / Python / 课程装置 / MQTT）</span></div>
      <div class="step"><span class="n">3</span><b>看曲线 · 打包数据集</b><span class="muted small">「数据可视化」看实时曲线 →「打包为数据集」算 DQS → 提交审核</span></div>
    </div>
    <p class="muted small" style="margin-top:10px">⚠️ 设备 Token 只在注册时显示一次，请立即保存；丢了就「停用」旧设备再注册一个新的。</p>
  </div>

  <div class="card">
    <h3>路径 A · 浏览器一键体验（无需任何代码）</h3>
    <p class="muted small">「我的设备」→ 设备行的「灌测试数据」按钮 → 输入 Token，立即写入 20 条温度数据。适合第一次熟悉流程。</p>
  </div>

  <div class="card">
    <h3>路径 B · HTTP 上报（任何能联网的语言/设备）<button class="btn gh sm" @click="copy(curlExample)">复制 curl</button></h3>
    <p class="muted small">向 <code>POST /api/v1/data</code> 发 JSON 数组，请求头带 <code>X-Device-Id</code> 与 <code>X-Device-Token</code>：</p>
    <pre class="codebox">{{ curlExample }}</pre>
    <p class="muted small" style="margin-top:10px">Python 版（持续采集示例）：<button class="btn gh sm" @click="copy(pyExample)">复制</button></p>
    <pre class="codebox">{{ pyExample }}</pre>
    <p class="muted small">每个点可选字段：<code>device_ts</code>（设备时间戳）、<code>lat</code>/<code>lon</code>（坐标，缺省用设备注册位置）。一次最多建议 ≤100 点。</p>
  </div>

  <div class="card">
    <h3>路径 C · 课程实验装置（STM32 → PC 网关）<button class="btn gh sm" @click="copy(gatewayExample)">复制命令</button></h3>
    <p class="muted small">《电气测试技术课程设计》装置专用：STM32 经 USB 串口逐行输出 <code>指标,数值</code>（如 <code>current,0.83</code>），电脑跑网关脚本转发上平台，<b>不需要任何联网硬件</b>。</p>
    <pre class="codebox">{{ gatewayExample }}</pre>
    <p class="muted small">网关脚本与 STM32 例程：GitHub 仓库 <code>tools/edu/</code>（pc_gateway.py · stm32_uart_report.c · stm32_esp01_report.c），向任课教师索取或自行下载。⚠️ ACS712/TA12 的 0–5V 输出须分压后再进 STM32 的 3.3V ADC。</p>
  </div>

  <div class="card">
    <h3>路径 D · MQTT 上报（物联网设备/ESP32）<button class="btn gh sm" @click="copy(mqttExample)">复制</button></h3>
    <pre class="codebox">{{ mqttExample }}</pre>
    <p class="muted small">单点也可以：<code>{"token":"...","metric":"temperature","value":23.5}</code>。报文里的 <code>token</code> 即设备 Token，用于身份校验。</p>
  </div>

  <div class="card">
    <h3>进阶 · Python SDK<button class="btn gh sm" @click="copy(sdkExample)">复制</button></h3>
    <p class="muted small">仓库 <code>sdk/sensemble_sdk.py</code>（依赖 requests），登录/注册设备/上报三步搞定：</p>
    <pre class="codebox">{{ sdkExample }}</pre>
  </div>

  <div class="card">
    <h3>常见问题</h3>
    <table>
      <thead><tr><th style="width:220px">问题</th><th>解决</th></tr></thead>
      <tbody>
        <tr><td>401 设备 Token 无效</td><td>设备ID 或 Token 写错；Token 丢失则停用旧设备、重新注册拿新 Token。</td></tr>
        <tr><td>429 上报过于频繁</td><td>平台限流：同一设备上报间隔 ≥1 秒，加大发送间隔即可。</td></tr>
        <tr><td>可视化看不到数据</td><td>确认所选设备/指标名与上报的 <code>metric</code> 一致；把时间范围调大；先点「刷新」。</td></tr>
        <tr><td>打包数据集 DQS 偏低</td><td>采样要连续（按设备注册时的采样周期）、补全元数据（型号/精度/校准日期）、减少异常值。</td></tr>
        <tr><td>数据集要公开给全班</td><td>打包时可见性选「公开」→ 提交审核 → 教师通过后全员可在「数据集广场」检索下载。</td></tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.steps { display: flex; flex-direction: column; gap: 10px; }
.step { display: flex; align-items: baseline; gap: 10px; }
.step .n { flex: 0 0 auto; width: 22px; height: 22px; line-height: 22px; text-align: center; border-radius: 50%;
  background: linear-gradient(135deg, #0E8C82, #7C3AED); color: #fff; font-size: 12px; font-weight: 700; }
.step b { flex: 0 0 auto; }
.codebox { background: #0B1220; color: #d8e1ec; border-radius: 10px; padding: 12px 14px; font-family: Consolas, monospace;
  font-size: 12.5px; line-height: 1.6; overflow-x: auto; white-space: pre; }
code { background: #f1f5f9; border-radius: 4px; padding: 1px 5px; font-family: Consolas, monospace; font-size: 12.5px; }
</style>
