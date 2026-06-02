<script setup>
import { ref, onMounted } from 'vue'
import { datasetApi, metaApi } from '../api'
import { toast } from '../toast'

const list = ref([])
const keyword = ref('')
const sort = ref('time')
const stName = { published: '已发布', pending: '待审核', draft: '草稿', rejected: '已退回' }

const sensorTypes = ref([])

// 编辑元数据
const showEdit = ref(false)
const editId = ref('')
const baseMeta = ref({})   // 保留未在表单中编辑的 meta 键（如 dqs_detail）
const editForm = ref({ name: '', description: '', sensor_type: '', accuracy: '', sample_interval: 60, calibration_date: '', location: '', tags: '' })
const savingEdit = ref(false)

// 版本历史
const showVer = ref(false)
const verOf = ref('')
const versions = ref([])

function editable(d) { return d.status === 'draft' || d.status === 'rejected' }

async function load() {
  try {
    list.value = (await datasetApi.list({ keyword: keyword.value || undefined, sort: sort.value })).data
  } catch (e) { /* 后端未起 */ }
}
async function loadSensorTypes() {
  try { sensorTypes.value = (await metaApi.sensorTypes()).data } catch (e) { /* noop */ }
}

async function openEdit(d) {
  try {
    const { data } = await datasetApi.detail(d.dataset_id)
    const m = data.meta || {}
    baseMeta.value = m
    editId.value = data.dataset_id
    editForm.value = {
      name: data.name || '',
      description: data.description || '',
      sensor_type: m.sensor_type || '',
      accuracy: m.accuracy || '',
      sample_interval: m.sample_interval || 60,
      calibration_date: m.calibration_date || '',
      location: m.location || '',
      tags: (data.tags || []).join(', ')
    }
    showEdit.value = true
  } catch (e) { toast(e?.response?.data?.detail || '无法加载详情') }
}
function onPickSensor() {
  const t = sensorTypes.value.find(s => s.model === editForm.value.sensor_type)
  if (t && t.accuracy) editForm.value.accuracy = t.accuracy
}
async function saveEdit() {
  savingEdit.value = true
  try {
    const f = editForm.value
    const meta = {
      ...baseMeta.value,
      sensor_type: f.sensor_type, accuracy: f.accuracy,
      sample_interval: Number(f.sample_interval) || 60,
      calibration_date: f.calibration_date, location: f.location
    }
    const tags = f.tags.split(',').map(s => s.trim()).filter(Boolean)
    const { data } = await datasetApi.update(editId.value, { name: f.name, description: f.description, meta, tags })
    toast(`已保存（版本 v${data.saved_version}）`)
    showEdit.value = false
    await load()
  } catch (e) { toast(e?.response?.data?.detail || '保存失败') }
  finally { savingEdit.value = false }
}

async function openVersions(d) {
  verOf.value = d.dataset_id
  versions.value = []
  showVer.value = true
  try { versions.value = (await datasetApi.versions(d.dataset_id)).data }
  catch (e) { toast(e?.response?.data?.detail || '无法加载版本历史') }
}

async function submit(d) {
  try { await datasetApi.submit(d.dataset_id); toast('已提交审核'); await load() }
  catch (e) { toast(e?.response?.data?.detail || '提交失败') }
}
async function download(d) {
  try {
    const res = await datasetApi.download(d.dataset_id, 'csv')
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url; a.download = `${d.dataset_id}.csv`; a.click()
    URL.revokeObjectURL(url)
    toast(`已下载 ${d.dataset_id}.csv`)
  } catch (e) { toast(e?.response?.data?.detail || '无权下载或失败') }
}
onMounted(() => { load(); loadSensorTypes() })
</script>

<template>
  <div class="controls">
    <input v-model="keyword" placeholder="🔍 搜索数据集（名称）" style="flex:1;min-width:220px" @keyup.enter="load">
    <select v-model="sort" @change="load">
      <option value="time">最新</option>
      <option value="dqs">质量最高</option>
      <option value="downloads">下载最多</option>
    </select>
    <button class="btn gh sm" @click="load">搜索</button>
  </div>

  <div class="grid">
    <div class="dcard" v-for="d in list" :key="d.dataset_id">
      <div class="t">{{ d.name }}</div>
      <div class="meta">
        {{ d.dataset_id }}
        <span v-if="d.archived" title="原始数据已归档至对象存储"> · 📦 已归档</span>
        <br>创建于 {{ d.created_at ? new Date(d.created_at).toLocaleDateString() : '-' }}
      </div>
      <div class="row">
        <span class="badge" :class="d.grade">DQS {{ d.dqs ?? '-' }} · {{ d.grade ?? '-' }}</span>
        <span class="st" :class="d.status">{{ stName[d.status] }}</span>
      </div>
      <div class="row">
        <span class="muted small">⬇ {{ d.downloads }} 次</span>
        <span style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">
          <button v-if="editable(d)" class="btn gh sm" @click="openEdit(d)">编辑</button>
          <button v-if="editable(d)" class="btn gh sm" @click="openVersions(d)">版本</button>
          <button v-if="editable(d)" class="btn gh sm" @click="submit(d)">提交审核</button>
          <button class="btn pri sm" @click="download(d)">下载</button>
        </span>
      </div>
    </div>
    <div v-if="!list.length" class="muted">暂无数据集。去「数据可视化」打包一个。</div>
  </div>

  <!-- 编辑元数据（FR-5.3：仅草稿/已退回可改，保存自动留存版本） -->
  <div class="mask" v-if="showEdit" @click.self="showEdit = false">
    <div class="modal">
      <h3>编辑数据集元数据</h3>
      <p class="muted small">仅草稿/已退回状态可编辑；每次保存会自动留存上一版为历史版本。</p>
      <label>名称</label><input v-model="editForm.name" style="width:100%">
      <label>描述</label><textarea v-model="editForm.description" rows="2" style="width:100%"></textarea>
      <label>传感器型号</label>
      <select v-model="editForm.sensor_type" style="width:100%" @change="onPickSensor">
        <option value="">（不指定）</option>
        <option v-for="s in sensorTypes" :key="s.model" :value="s.model">
          {{ s.model + (s.metrics.length ? ' · ' + s.metrics.join('/') : '') }}
        </option>
      </select>
      <label>精度</label><input v-model="editForm.accuracy" placeholder="如 ±0.5℃" style="width:100%">
      <label>采样周期（秒）</label><input v-model.number="editForm.sample_interval" type="number" style="width:100%">
      <label>校准日期</label><input v-model="editForm.calibration_date" type="date" style="width:100%">
      <label>安装位置</label><input v-model="editForm.location" placeholder="如 实验楼B-205" style="width:100%">
      <label>标签（逗号分隔）</label><input v-model="editForm.tags" placeholder="如 温度, 教学楼, 2026春" style="width:100%">
      <div class="acts">
        <button class="btn gh" @click="showEdit = false">取消</button>
        <button class="btn pri" :disabled="savingEdit" @click="saveEdit">保存并留存版本</button>
      </div>
    </div>
  </div>

  <!-- 版本历史 -->
  <div class="mask" v-if="showVer" @click.self="showVer = false">
    <div class="modal" style="width:560px">
      <h3>版本历史 · {{ verOf }}</h3>
      <p class="muted small">每次编辑保存前的快照，最新在前。</p>
      <table>
        <thead><tr><th>版本</th><th>名称</th><th>型号</th><th>精度</th><th>保存时间</th></tr></thead>
        <tbody>
          <tr v-for="v in versions" :key="v.version">
            <td>v{{ v.version }}</td>
            <td>{{ v.name }}</td>
            <td>{{ v.meta?.sensor_type || '-' }}</td>
            <td>{{ v.meta?.accuracy || '-' }}</td>
            <td>{{ v.created_at ? new Date(v.created_at).toLocaleString() : '-' }}</td>
          </tr>
          <tr v-if="!versions.length"><td colspan="5" class="muted">暂无历史版本（尚未编辑过）。</td></tr>
        </tbody>
      </table>
      <div class="acts">
        <button class="btn gh" @click="showVer = false">关闭</button>
      </div>
    </div>
  </div>
</template>
