<script setup>
import { ref, onMounted } from 'vue'
import { deviceApi, dataApi } from '../api'
import { toast } from '../toast'

const devices = ref([])
const showReg = ref(false)
const newToken = ref('')
const saving = ref(false)
const form = ref({ device_id: '', type: 'ESP32', location: '', sample_interval: 60 })
const tokenModal = ref({ show: false, id: '', token: '' })

async function load() {
  try { devices.value = (await deviceApi.list()).data } catch (e) { /* 后端未起 */ }
}
function openReg() {
  newToken.value = ''
  form.value = { device_id: '', type: 'ESP32', location: '', sample_interval: 60 }
  showReg.value = true
}
async function register() {
  saving.value = true
  try {
    const { data } = await deviceApi.create(form.value)
    newToken.value = data.device_token
    await load()
    toast('设备已注册')
  } catch (e) { toast(e?.response?.data?.detail || '注册失败') }
  finally { saving.value = false }
}
async function copyText(text, okMsg = '已复制') {
  try { await navigator.clipboard.writeText(text); toast(okMsg) }
  catch (e) {
    const ta = document.createElement('textarea'); ta.value = text
    document.body.appendChild(ta); ta.select()
    const ok = document.execCommand('copy'); document.body.removeChild(ta)
    toast(ok ? okMsg : '复制失败，请手动选择')
  }
}
function copyToken(d) {
  if (!d.token) { toast('该设备暂无可见 Token，请点「重置」生成一个'); return }
  copyText(d.token, 'Token 已复制')
}
async function resetToken(d) {
  if (!confirm(`重置设备「${d.device_id}」的 Token？\n旧 Token 立即失效，用旧 Token 上报的程序需更新为新值。`)) return
  try {
    const { data } = await deviceApi.rotateToken(d.device_id)
    await load()
    tokenModal.value = { show: true, id: d.device_id, token: data.device_token }
  } catch (e) { toast(e?.response?.data?.detail || '重置失败') }
}
async function seed(dev) {
  const token = dev.token || prompt(`输入设备「${dev.device_id}」的 Token，灌入 20 条测试数据：`)
  if (!token) return
  const points = []
  for (let i = 0; i < 20; i++) points.push({ metric: 'temperature', value: +(23 + 3 * Math.sin(i / 3) + (Math.random() - 0.5)).toFixed(2) })
  try {
    await dataApi.ingest(dev.device_id, token, points)
    toast('已灌入 20 条 temperature 数据，去「数据可视化」查看'); await load()
  } catch (e) { toast(e?.response?.data?.detail || 'Token 无效或上报失败') }
}
async function deactivate(dev) {
  if (!confirm(`确定停用设备「${dev.device_id}」？`)) return
  const purge = confirm('是否同时清除该设备的历史数据？\n确定 = 清除，取消 = 保留')
  try {
    await deviceApi.deactivate(dev.device_id, purge)
    toast(purge ? '已停用并清除历史' : '已停用'); await load()
  } catch (e) { toast(e?.response?.data?.detail || '停用失败') }
}
onMounted(load)
</script>

<template>
  <div class="card">
    <h3>我的设备 <button class="btn pri sm" @click="openReg">+ 注册设备</button></h3>
    <p class="muted small" style="margin:-6px 0 12px">设备 Token 用于上报鉴权，可随时「复制」；一旦泄露就点「重置」（旧 Token 立即失效）。</p>
    <table>
      <thead><tr><th>设备ID</th><th>型号</th><th>在线</th><th>状态</th><th>最后上报</th><th>Token</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="d in devices" :key="d.device_id">
          <td><b>{{ d.device_id }}</b></td>
          <td>{{ d.type }}</td>
          <td><span class="dot" :class="d.online ? 'on' : 'off'"></span> {{ d.online ? '在线' : '离线' }}</td>
          <td><span class="st" :class="d.status === 'active' ? 'published' : 'draft'">{{ d.status === 'active' ? '启用' : '已停用' }}</span></td>
          <td>{{ d.last_seen ? new Date(d.last_seen).toLocaleString() : '未上报' }}</td>
          <td style="white-space:nowrap">
            <button class="btn gh sm" @click="copyToken(d)">复制</button>
            <button class="btn gh sm" style="margin-left:6px" @click="resetToken(d)">重置</button>
          </td>
          <td style="white-space:nowrap">
            <button class="btn gh sm" @click="seed(d)">灌测试数据</button>
            <button v-if="d.status === 'active'" class="btn no sm" style="margin-left:6px" @click="deactivate(d)">停用</button>
          </td>
        </tr>
        <tr v-if="!devices.length"><td colspan="7" class="muted">还没有设备，点右上「注册设备」。</td></tr>
      </tbody>
    </table>
  </div>

  <!-- 注册设备 -->
  <div class="mask" v-if="showReg" @click.self="showReg = false">
    <div class="modal">
      <h3>注册设备</h3>
      <template v-if="!newToken">
        <p class="muted small">注册后生成设备 Token（之后可随时在列表「复制 / 重置」）。</p>
        <label>设备 ID</label><input v-model="form.device_id" placeholder="esp32-003" style="width:100%">
        <label>型号</label><input v-model="form.type" placeholder="ESP32" style="width:100%">
        <label>安装位置</label><input v-model="form.location" placeholder="实验楼B-205" style="width:100%">
        <label>采样周期（秒）</label><input v-model.number="form.sample_interval" type="number" style="width:100%">
      </template>
      <template v-else>
        <label>设备 Token（已保存，可随时在列表复制）</label>
        <div class="tokenbox">{{ newToken }}</div>
      </template>
      <div class="acts">
        <button class="btn gh" @click="showReg = false">{{ newToken ? '完成' : '取消' }}</button>
        <button v-if="!newToken" class="btn pri" :disabled="saving || !form.device_id" @click="register">生成 Token 并注册</button>
        <button v-else class="btn pri" @click="copyText(newToken, 'Token 已复制')">复制 Token</button>
      </div>
    </div>
  </div>

  <!-- 重置后的新 Token -->
  <div class="mask" v-if="tokenModal.show" @click.self="tokenModal.show = false">
    <div class="modal">
      <h3>新 Token · {{ tokenModal.id }}</h3>
      <p class="muted small">旧 Token 已失效，请把上报程序里的 Token 换成下面这个：</p>
      <div class="tokenbox">{{ tokenModal.token }}</div>
      <div class="acts">
        <button class="btn gh" @click="tokenModal.show = false">完成</button>
        <button class="btn pri" @click="copyText(tokenModal.token, 'Token 已复制')">复制 Token</button>
      </div>
    </div>
  </div>
</template>
