<script setup>
import { ref, onMounted } from 'vue'
import { deviceApi, dataApi, datasetApi } from '../api'
import LineChart from '../components/LineChart.vue'
import { toast } from '../toast'

const devices = ref([])
const deviceId = ref('')
const metric = ref('temperature')
const hours = ref(24)
const rows = ref([])
const lineOption = ref(null)
const heatOption = ref(null)
const colors = { temperature: '#0E8C82', humidity: '#7C3AED', co2: '#DB2777' }
const unit = { temperature: '℃', humidity: '%', co2: 'ppm' }
const showPack = ref(false)
const pack = ref({ name: '', sensor_type: 'DHT22', accuracy: '±0.5℃', calibration_date: '2026-05-30', visibility: 'private' })

async function loadDevices() {
  try {
    devices.value = (await deviceApi.list()).data
    if (devices.value.length) deviceId.value = devices.value[0].device_id
    await refresh()
  } catch (e) { /* 后端未起 */ }
}

async function refresh() {
  await Promise.all([queryLine(), loadHeat()])
}

async function queryLine() {
  if (!deviceId.value) { lineOption.value = null; rows.value = []; return }
  const start = new Date(Date.now() - hours.value * 3600 * 1000).toISOString()
  try {
    const { data } = await dataApi.query({ device_id: deviceId.value, metric: metric.value, start })
    rows.value = data
    const c = colors[metric.value] || '#0E8C82'
    lineOption.value = {
      grid: { left: 46, right: 18, top: 24, bottom: 34 }, tooltip: { trigger: 'axis' },
      xAxis: { type: 'time' }, yAxis: { type: 'value', scale: true },
      series: [{
        type: 'line', smooth: true, showSymbol: false, name: metric.value,
        data: data.map(x => [x.ts, x.value]),
        lineStyle: { color: c, width: 2 }, areaStyle: { color: c + '22' }
      }]
    }
  } catch (e) { toast('查询失败') }
}

async function loadHeat() {
  try {
    const g = (await dataApi.heatmap(metric.value)).data.grid
    if (!g || !g.points || !g.points.length) { heatOption.value = null; return }
    const u = unit[metric.value] || ''
    heatOption.value = {
      tooltip: {
        formatter: (p) => p.seriesType === 'scatter'
          ? `${p.data[2]}：${p.data[3]} ${u}`
          : `${metric.value}: ${p.data[2]} ${u}`
      },
      grid: { left: 16, right: 86, top: 14, bottom: 14 },
      xAxis: { type: 'category', data: Array.from({ length: g.nx }, (_, i) => String(i)), show: false },
      yAxis: { type: 'category', data: Array.from({ length: g.ny }, (_, j) => String(j)), show: false },
      visualMap: {
        min: g.vmin, max: g.vmax, calculable: true, right: 10, top: 'center', precision: 1,
        text: [`高 ${u}`, `低 ${u}`],
        inRange: { color: ['#0E8C82', '#5E4AE3', '#7C3AED', '#DB2777'] }
      },
      series: [
        { type: 'heatmap', data: g.cells, progressive: 0, emphasis: { disabled: true }, itemStyle: { borderWidth: 0 } },
        {
          type: 'scatter', symbolSize: 12, z: 5,
          data: g.points.map(p => [p.i, p.j, p.device_id, p.value]),
          itemStyle: { color: '#fff', borderColor: '#0B1220', borderWidth: 2 },
          label: { show: true, formatter: (p) => p.data[2], position: 'top', color: '#0B1220', fontSize: 10 }
        }
      ]
    }
  } catch (e) { heatOption.value = null }
}

async function doPack() {
  const start = new Date(Date.now() - hours.value * 3600 * 1000).toISOString()
  const end = new Date().toISOString()
  try {
    const { data } = await datasetApi.create({
      name: pack.value.name || `${deviceId.value} ${metric.value}`,
      device_id: deviceId.value, start, end, visibility: pack.value.visibility,
      meta: {
        sensor_type: pack.value.sensor_type, accuracy: pack.value.accuracy,
        sample_interval: 60, location: '(见设备)', calibration_date: pack.value.calibration_date
      }
    })
    showPack.value = false
    toast(`已创建 ${data.dataset_id} · DQS ${data.dqs}(${data.grade})，去数据集广场提交审核`)
  } catch (e) { toast(e?.response?.data?.detail || '打包失败') }
}

onMounted(loadDevices)
</script>

<template>
  <div class="controls">
    <select v-model="deviceId" @change="queryLine">
      <option v-for="d in devices" :key="d.device_id" :value="d.device_id">{{ d.device_id }}</option>
    </select>
    <select v-model="metric" @change="refresh">
      <option value="temperature">温度 ℃</option>
      <option value="humidity">湿度 %</option>
      <option value="co2">CO₂ ppm</option>
    </select>
    <select v-model.number="hours" @change="queryLine">
      <option :value="24">最近 24 小时</option>
      <option :value="168">最近 7 天</option>
    </select>
    <button class="btn gh sm" @click="refresh">刷新</button>
    <button class="btn pri sm" :disabled="!rows.length" @click="showPack = true">打包为数据集</button>
  </div>

  <div class="card">
    <h3>时间序列（{{ deviceId || '无设备' }} · {{ metric }}）<span class="muted small">{{ rows.length }} 点</span></h3>
    <LineChart v-if="lineOption && rows.length" :option="lineOption" height="300px" />
    <div v-else class="muted small">无数据。请先在「我的设备」灌入测试数据或运行 tools/simulate.py。</div>
  </div>

  <div class="card">
    <h3>空间热力图 · IDW 插值（{{ metric }} · 全部设备最新值）</h3>
    <LineChart v-if="heatOption" :option="heatOption" height="340px" />
    <div v-else class="ph">需要 ≥1 个带经纬度的设备且有数据。运行 <code>python tools/simulate.py</code> 会生成 3 个带坐标的设备。</div>
  </div>

  <div class="mask" v-if="showPack" @click.self="showPack = false">
    <div class="modal">
      <h3>打包为数据集</h3>
      <p class="muted small">将当前设备在所选时间范围的数据打包，自动计算 DQS（三维 v1）。</p>
      <label>数据集名称</label><input v-model="pack.name" :placeholder="`${deviceId} ${metric}`" style="width:100%">
      <label>传感器型号</label><input v-model="pack.sensor_type" style="width:100%">
      <label>精度</label><input v-model="pack.accuracy" style="width:100%">
      <label>可见性</label>
      <select v-model="pack.visibility" style="width:100%">
        <option value="private">校内私有</option>
        <option value="public">公开</option>
      </select>
      <div class="acts">
        <button class="btn gh" @click="showPack = false">取消</button>
        <button class="btn pri" @click="doPack">打包并算 DQS</button>
      </div>
    </div>
  </div>
</template>
