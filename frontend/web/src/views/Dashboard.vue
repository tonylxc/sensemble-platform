<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { statsApi, dataApi, deviceApi } from '../api'
import LineChart from '../components/LineChart.vue'

const router = useRouter()

const s = ref(null)            // stats/overview
const devices = ref([])
const heatOption = ref(null)
const metric = ref('temperature')
const clock = ref('')
const today = ref('')
const lastRefresh = ref('')
const isFull = ref(false)

const METRICS = [
  { k: 'temperature', label: '温度', unit: '℃' },
  { k: 'humidity', label: '湿度', unit: '%' },
  { k: 'co2', label: 'CO₂', unit: 'ppm' }
]
const stName = { published: '已发布', pending: '待审核', draft: '草稿', rejected: '已退回' }
const statusColor = { published: '#34d399', pending: '#fbbf24', draft: '#94a3b8', rejected: '#f87171' }
const gradeColor = { A: '#34d399', B: '#fbbf24', C: '#94a3b8', D: '#f87171', '-': '#475569' }

function fmt(n) { return (n ?? 0).toLocaleString('zh-CN') }

const statusList = computed(() => {
  const by = s.value?.datasets?.by_status || {}
  return ['published', 'pending', 'draft', 'rejected']
    .filter(k => k in by).map(k => ({ key: k, label: stName[k] || k, count: by[k] }))
})
const gradeList = computed(() => {
  const g = s.value?.grade_distribution || {}
  return Object.keys(g).sort().map(k => ({ key: k, count: g[k] }))
})
const maxStatus = computed(() => Math.max(1, ...statusList.value.map(x => x.count)))
const maxGrade = computed(() => Math.max(1, ...gradeList.value.map(x => x.count)))
const onlineCount = computed(() => devices.value.filter(d => d.online).length)
const metricUnit = computed(() => METRICS.find(m => m.k === metric.value)?.unit || '')

function buildHeat(grid) {
  if (!grid || !grid.points || !grid.points.length) { heatOption.value = null; return }
  const u = metricUnit.value
  heatOption.value = {
    backgroundColor: 'transparent',
    tooltip: {
      backgroundColor: 'rgba(11,18,32,.92)', borderColor: 'rgba(255,255,255,.12)',
      textStyle: { color: '#e2e8f0' },
      formatter: (p) => p.seriesType === 'scatter'
        ? `${p.data[2]}：${p.data[3]} ${u}` : `${metric.value}: ${p.data[2]} ${u}`
    },
    grid: { left: 16, right: 92, top: 14, bottom: 14 },
    xAxis: { type: 'category', data: Array.from({ length: grid.nx }, (_, i) => String(i)), show: false },
    yAxis: { type: 'category', data: Array.from({ length: grid.ny }, (_, j) => String(j)), show: false },
    visualMap: {
      min: grid.vmin, max: grid.vmax, calculable: true, right: 12, top: 'center', precision: 1,
      text: [`高 ${u}`, `低 ${u}`], textStyle: { color: '#cbd5e1' },
      inRange: { color: ['#0E8C82', '#5E4AE3', '#7C3AED', '#DB2777'] }
    },
    series: [
      { type: 'heatmap', data: grid.cells, progressive: 0, emphasis: { disabled: true }, itemStyle: { borderWidth: 0 } },
      {
        type: 'scatter', symbolSize: 13, z: 5,
        data: grid.points.map(p => [p.i, p.j, p.device_id, p.value]),
        itemStyle: { color: '#fff', borderColor: '#5EEAD4', borderWidth: 2, shadowColor: '#5EEAD4', shadowBlur: 8 },
        label: { show: true, formatter: (p) => p.data[2], position: 'top', color: '#e2e8f0', fontSize: 10 }
      }
    ]
  }
}

async function loadStats() {
  try { s.value = (await statsApi.overview()).data } catch (e) { /* 需教师/管理员 */ }
}
async function loadDevices() {
  try { devices.value = (await deviceApi.list()).data } catch (e) { /* noop */ }
}
async function loadHeat() {
  try { buildHeat((await dataApi.heatmap(metric.value)).data.grid) } catch (e) { heatOption.value = null }
}
async function refresh() {
  await Promise.all([loadStats(), loadDevices(), loadHeat()])
  lastRefresh.value = new Date().toLocaleTimeString('zh-CN')
}
function switchMetric(k) { metric.value = k; loadHeat() }

function tick() {
  const d = new Date()
  clock.value = d.toLocaleTimeString('zh-CN', { hour12: false })
  today.value = d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
}
function toggleFull() {
  if (document.fullscreenElement) document.exitFullscreen()
  else document.documentElement.requestFullscreen?.()
}
function onFullChange() { isFull.value = !!document.fullscreenElement }

let dataTimer = null, clockTimer = null
onMounted(() => {
  tick(); refresh()
  clockTimer = setInterval(tick, 1000)
  dataTimer = setInterval(refresh, 15000)
  document.addEventListener('fullscreenchange', onFullChange)
})
onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  if (dataTimer) clearInterval(dataTimer)
  document.removeEventListener('fullscreenchange', onFullChange)
})
</script>

<template>
  <div class="screen">
    <header class="bar">
      <div class="brand">
        <img src="/logo.svg" alt="众感">
        <div>
          <div class="bt">众感 Sensemble · 实验室大屏</div>
          <div class="bs">算电智创实验室 · 开放感知数据平台</div>
        </div>
      </div>
      <div class="bar-r">
        <div class="clock">
          <div class="t">{{ clock }}</div>
          <div class="d">{{ today }}</div>
        </div>
        <button class="gbtn" @click="toggleFull">{{ isFull ? '退出全屏' : '全屏' }}</button>
        <button class="gbtn" @click="router.push('/overview')">返回控制台</button>
      </div>
    </header>

    <section class="kpis">
      <div class="kpi"><div class="n teal">{{ fmt(s?.users) }}</div><div class="l">注册用户</div></div>
      <div class="kpi"><div class="n purple">{{ fmt(s?.devices) }}</div><div class="l">接入设备</div></div>
      <div class="kpi"><div class="n magenta">{{ fmt(s?.data_points) }}</div><div class="l">累计数据点</div></div>
      <div class="kpi"><div class="n teal">{{ fmt(s?.datasets?.total) }}</div><div class="l">数据集</div></div>
      <div class="kpi"><div class="n purple">{{ fmt(s?.downloads) }}</div><div class="l">总下载次数</div></div>
    </section>

    <main class="grid">
      <div class="panel hero">
        <div class="ph-head">
          <h3>空间分布热力图 · IDW 插值<span class="sub">全部设备最新值</span></h3>
          <div class="seg">
            <button v-for="m in METRICS" :key="m.k" :class="{ on: metric === m.k }" @click="switchMetric(m.k)">{{ m.label }}</button>
          </div>
        </div>
        <LineChart v-if="heatOption" :option="heatOption" height="calc(100% - 44px)" />
        <div v-else class="empty">暂无可插值数据 · 需 ≥1 个带经纬度的设备且有该指标数据</div>
      </div>

      <div class="side">
        <div class="panel">
          <h3>数据集状态分布</h3>
          <div v-for="x in statusList" :key="x.key" class="bar-row">
            <span class="bl">{{ x.label }}</span>
            <span class="track"><span class="fill" :style="{ width: (x.count / maxStatus * 100) + '%', background: statusColor[x.key] }"></span></span>
            <span class="bn">{{ x.count }}</span>
          </div>
          <div v-if="!statusList.length" class="empty sm">暂无数据集</div>
        </div>

        <div class="panel">
          <h3>已发布质量分级（DQS）</h3>
          <div v-for="x in gradeList" :key="x.key" class="bar-row">
            <span class="bl"><span class="gtag" :style="{ background: gradeColor[x.key] || '#475569' }">{{ x.key }}</span></span>
            <span class="track"><span class="fill" :style="{ width: (x.count / maxGrade * 100) + '%', background: gradeColor[x.key] || '#475569' }"></span></span>
            <span class="bn">{{ x.count }}</span>
          </div>
          <div v-if="!gradeList.length" class="empty sm">暂无已发布数据集</div>
        </div>

        <div class="panel devs">
          <h3>设备在线 <span class="sub">本账号 · {{ onlineCount }}/{{ devices.length }} 在线</span></h3>
          <div class="dlist">
            <div v-for="d in devices" :key="d.device_id" class="drow">
              <span class="dot" :class="d.online ? 'on' : 'off'"></span>
              <span class="did">{{ d.device_id }}</span>
              <span class="dty">{{ d.type || '-' }}</span>
              <span class="dls">{{ d.last_seen ? new Date(d.last_seen).toLocaleTimeString('zh-CN') : '未上报' }}</span>
            </div>
            <div v-if="!devices.length" class="empty sm">本账号暂无设备</div>
          </div>
        </div>
      </div>
    </main>

    <footer class="foot">
      <span>众感汇流，数据共鸣 · Every sensor, one ensemble.</span>
      <span>每 15 秒自动刷新 · 上次刷新 {{ lastRefresh || '—' }}</span>
    </footer>
  </div>
</template>

<style scoped>
.screen { height: 100vh; background:
  radial-gradient(900px 500px at 85% -8%, rgba(219,39,119,.16), transparent),
  radial-gradient(900px 600px at 5% 110%, rgba(124,58,237,.20), transparent),
  linear-gradient(160deg, #0B1220, #0d1530 60%, #120d2e);
  color: #e2e8f0; display: flex; flex-direction: column; padding: 18px 22px; gap: 14px; overflow: hidden; }

.bar { display: flex; align-items: center; justify-content: space-between; }
.bar .brand { display: flex; align-items: center; gap: 12px; }
.bar .brand img { width: 40px; height: 40px; }
.bar .bt { font-size: 20px; font-weight: 800; letter-spacing: .5px; }
.bar .bs { font-size: 12px; color: #5EEAD4; margin-top: 2px; }
.bar-r { display: flex; align-items: center; gap: 16px; }
.clock { text-align: right; }
.clock .t { font-size: 22px; font-weight: 800; font-variant-numeric: tabular-nums; color: #fff; }
.clock .d { font-size: 11px; color: #94a3b8; }
.gbtn { background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12); color: #cbd5e1;
  border-radius: 9px; padding: 7px 13px; font-size: 12.5px; cursor: pointer; }
.gbtn:hover { border-color: #5EEAD4; color: #fff; }

.kpis { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.kpi { background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.08); border-radius: 16px; padding: 16px 18px; }
.kpi .n { font-size: 34px; font-weight: 800; font-variant-numeric: tabular-nums; line-height: 1.1; }
.kpi .l { color: #94a3b8; font-size: 13px; margin-top: 6px; }
.kpi .teal { color: #5EEAD4; } .kpi .purple { color: #a78bfa; } .kpi .magenta { color: #f472b6; }

.grid { flex: 1; min-height: 0; display: grid; grid-template-columns: 2fr 1fr; gap: 14px; }
.panel { background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.08); border-radius: 16px; padding: 16px; }
.panel h3 { font-size: 15px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; gap: 10px; font-weight: 700; }
.panel h3 .sub { font-size: 12px; color: #94a3b8; font-weight: 400; }
.hero { display: flex; flex-direction: column; min-height: 0; }
.ph-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.ph-head h3 { margin: 0; }
.ph-head .sub { font-size: 12px; color: #94a3b8; font-weight: 400; margin-left: 8px; }
.seg { display: flex; gap: 4px; background: rgba(255,255,255,.05); border-radius: 9px; padding: 3px; }
.seg button { background: transparent; border: 0; color: #cbd5e1; padding: 5px 12px; border-radius: 7px; font-size: 12.5px; cursor: pointer; }
.seg button.on { background: linear-gradient(90deg, #0E8C82, #7C3AED); color: #fff; font-weight: 600; }

.side { display: flex; flex-direction: column; gap: 14px; min-height: 0; }
.side .panel { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.devs .dlist { overflow: auto; flex: 1; }

.bar-row { display: flex; align-items: center; gap: 10px; margin: 9px 0; }
.bar-row .bl { width: 56px; font-size: 13px; color: #cbd5e1; flex: 0 0 auto; }
.bar-row .track { flex: 1; height: 10px; background: rgba(255,255,255,.06); border-radius: 999px; overflow: hidden; }
.bar-row .fill { display: block; height: 100%; border-radius: 999px; transition: width .5s ease; }
.bar-row .bn { width: 40px; text-align: right; font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }
.gtag { display: inline-block; width: 20px; height: 20px; line-height: 20px; text-align: center; border-radius: 6px; color: #0B1220; font-weight: 800; font-size: 12px; }

.drow { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,.05); font-size: 13px; }
.drow .dot { width: 9px; height: 9px; border-radius: 50%; flex: 0 0 auto; }
.drow .dot.on { background: #34d399; box-shadow: 0 0 8px #34d399; }
.drow .dot.off { background: #475569; }
.drow .did { font-weight: 600; color: #fff; }
.drow .dty { color: #94a3b8; }
.drow .dls { margin-left: auto; color: #94a3b8; font-size: 12px; }

.empty { flex: 1; display: grid; place-items: center; color: #64748b; font-size: 13px;
  border: 1px dashed rgba(255,255,255,.1); border-radius: 12px; }
.empty.sm { padding: 18px; border: 0; }

.foot { display: flex; justify-content: space-between; color: #64748b; font-size: 12px; }
.foot span:first-child { color: #5EEAD4; }
</style>
