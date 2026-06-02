<script setup>
import { ref, onMounted } from 'vue'
import { deviceApi, dataApi } from '../api'
import { toast } from '../toast'

const devices = ref([])
const showModal = ref(false)
const newToken = ref('')
const saving = ref(false)
const form = ref({ device_id: '', type: 'ESP32', location: '', sample_interval: 60 })

async function load() {
  try { devices.value = (await deviceApi.list()).data } catch (e) { /* 后端未起 */ }
}
function openModal() {
  newToken.value = ''
  form.value = { device_id: '', type: 'ESP32', location: '', sample_interval: 60 }
  showModal.value = true
}
async function register() {
  saving.value = true
  try {
    const { data } = await deviceApi.create(form.value)
    newToken.value = data.device_token
    await load()
    toast('设备已注册，请保存 Token')
  } catch (e) {
    toast(e?.response?.data?.detail || '注册失败')
  } finally { saving.value = false }
}
async function seed(dev) {
  const token = prompt(`输入设备「${dev.device_id}」的 Token（注册时显示的那一次），灌入 20 条测试数据：`)
  if (!token) return
  const points = []
  for (let i = 0; i < 20; i++) {
    points.push({ metric: 'temperature', value: +(23 + 3 * Math.sin(i / 3) + (Math.random() - 0.5)).toFixed(2) })
  }
  try {
    await dataApi.ingest(dev.device_id, token, points)
    toast('已灌入 20 条 temperature 数据，去「数据可视化」查看')
    await load()
  } catch (e) {
    toast(e?.response?.data?.detail || 'Token 无效或上报失败')
  }
}
async function deactivate(dev) {
  if (!confirm(`确定停用设备「${dev.device_id}」？`)) return
  const purge = confirm('是否同时清除该设备的历史数据？\n确定 = 清除，取消 = 保留')
  try {
    await deviceApi.deactivate(dev.device_id, purge)
    toast(purge ? '已停用并清除历史' : '已停用')
    await load()
  } catch (e) {
    toast(e?.response?.data?.detail || '停用失败')
  }
}
onMounted(load)
</script>

<template>
  <div class="card">
    <h3>我的设备 <button class="btn pri sm" @click="openModal">+ 注册设备</button></h3>
    <table>
      <thead><tr><th>设备ID</th><th>型号</th><th>在线</th><th>状态</th><th>最后上报</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="d in devices" :key="d.device_id">
          <td><b>{{ d.device_id }}</b></td>
          <td>{{ d.type }}</td>
          <td><span class="dot" :class="d.online ? 'on' : 'off'"></span> {{ d.online ? '在线' : '离线' }}</td>
          <td><span class="st" :class="d.status === 'active' ? 'published' : 'draft'">{{ d.status === 'active' ? '启用' : '已停用' }}</span></td>
          <td>{{ d.last_seen ? new Date(d.last_seen).toLocaleString() : '未上报' }}</td>
          <td>
            <button class="btn gh sm" @click="seed(d)">灌测试数据</button>
            <button v-if="d.status === 'active'" class="btn no sm" style="margin-left:6px" @click="deactivate(d)">停用</button>
          </td>
        </tr>
        <tr v-if="!devices.length"><td colspan="6" class="muted">还没有设备，点右上「注册设备」。</td></tr>
      </tbody>
    </table>
  </div>

  <div class="mask" v-if="showModal" @click.self="showModal = false">
    <div class="modal">
      <h3>注册设备</h3>
      <p class="muted small">注册成功后返回一次性设备 Token，用于上报鉴权（一机一 Token）。</p>
      <template v-if="!newToken">
        <label>设备 ID</label><input v-model="form.device_id" placeholder="esp32-003" style="width:100%">
        <label>型号</label><input v-model="form.type" placeholder="ESP32" style="width:100%">
        <label>安装位置</label><input v-model="form.location" placeholder="实验楼B-205" style="width:100%">
        <label>采样周期（秒）</label><input v-model.number="form.sample_interval" type="number" style="width:100%">
      </template>
      <template v-else>
        <label>设备 Token（仅此一次，请复制保存）</label>
        <div class="tokenbox">{{ newToken }}</div>
      </template>
      <div class="acts">
        <button class="btn gh" @click="showModal = false">{{ newToken ? '完成' : '取消' }}</button>
        <button v-if="!newToken" class="btn pri" :disabled="saving || !form.device_id" @click="register">生成 Token 并注册</button>
      </div>
    </div>
  </div>
</template>
