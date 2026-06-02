<script setup>
import { ref, onMounted } from 'vue'
import { deviceApi, datasetApi, dataApi } from '../api'
import LineChart from '../components/LineChart.vue'

const devices = ref([])
const datasets = ref([])
const chartOption = ref(null)
const stName = { published: '已发布', pending: '待审核', draft: '草稿', rejected: '已退回' }

function publishedCount() { return datasets.value.filter(d => d.status === 'published').length }
function pendingCount() { return datasets.value.filter(d => d.status === 'pending').length }

async function load() {
  try {
    const [d, ds] = await Promise.all([deviceApi.list(), datasetApi.list({ sort: 'time' })])
    devices.value = d.data
    datasets.value = ds.data
    if (devices.value.length) {
      const dev = devices.value[0]
      const r = await dataApi.query({ device_id: dev.device_id, limit: 500 })
      buildChart(r.data)
    }
  } catch (e) { /* 后端未起时静默 */ }
}

function buildChart(rows) {
  if (!rows.length) return
  const metric = rows[0].metric
  const data = rows.filter(x => x.metric === metric).map(x => [x.ts, x.value])
  chartOption.value = {
    grid: { left: 44, right: 18, top: 24, bottom: 34 }, tooltip: { trigger: 'axis' },
    xAxis: { type: 'time' }, yAxis: { type: 'value', scale: true },
    series: [{ type: 'line', smooth: true, showSymbol: false, name: metric, data,
      lineStyle: { color: '#0E8C82' }, areaStyle: { color: 'rgba(14,140,130,.12)' } }]
  }
}

onMounted(load)
</script>

<template>
  <div class="stats">
    <div class="stat"><div class="n t">{{ devices.length }}</div><div class="l">我的设备</div></div>
    <div class="stat"><div class="n p">{{ datasets.length }}</div><div class="l">可见数据集</div></div>
    <div class="stat"><div class="n m">{{ publishedCount() }}</div><div class="l">已发布</div></div>
    <div class="stat"><div class="n i">{{ pendingCount() }}</div><div class="l">待审核</div></div>
  </div>

  <div class="card">
    <h3>最近数据 · ECharts 折线</h3>
    <LineChart v-if="chartOption" :option="chartOption" height="260px" />
    <div v-else class="muted small">暂无数据。去「我的设备」注册设备并用「灌测试数据」造几条，再回来看。</div>
  </div>

  <div class="card">
    <h3>最近数据集</h3>
    <table>
      <thead><tr><th>编号</th><th>名称</th><th>DQS</th><th>状态</th><th>下载</th></tr></thead>
      <tbody>
        <tr v-for="d in datasets.slice(0, 6)" :key="d.dataset_id">
          <td>{{ d.dataset_id }}</td>
          <td>{{ d.name }}</td>
          <td><span class="badge" :class="d.grade">{{ d.grade }} · {{ d.dqs }}</span></td>
          <td><span class="st" :class="d.status">{{ stName[d.status] }}</span></td>
          <td>{{ d.downloads }}</td>
        </tr>
        <tr v-if="!datasets.length"><td colspan="5" class="muted">暂无数据集</td></tr>
      </tbody>
    </table>
  </div>
</template>
