<script setup>
import { ref, onMounted } from 'vue'
import { datasetApi } from '../api'
import { toast } from '../toast'

const list = ref([])
const keyword = ref('')
const sort = ref('time')
const stName = { published: '已发布', pending: '待审核', draft: '草稿', rejected: '已退回' }

async function load() {
  try {
    list.value = (await datasetApi.list({ keyword: keyword.value || undefined, sort: sort.value })).data
  } catch (e) { /* 后端未起 */ }
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
onMounted(load)
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
      <div class="meta">{{ d.dataset_id }}<br>创建于 {{ d.created_at ? new Date(d.created_at).toLocaleDateString() : '-' }}</div>
      <div class="row">
        <span class="badge" :class="d.grade">DQS {{ d.dqs ?? '-' }} · {{ d.grade ?? '-' }}</span>
        <span class="st" :class="d.status">{{ stName[d.status] }}</span>
      </div>
      <div class="row">
        <span class="muted small">⬇ {{ d.downloads }} 次</span>
        <span style="display:flex;gap:6px">
          <button v-if="d.status === 'draft' || d.status === 'rejected'" class="btn gh sm" @click="submit(d)">提交审核</button>
          <button class="btn pri sm" @click="download(d)">下载 CSV</button>
        </span>
      </div>
    </div>
    <div v-if="!list.length" class="muted">暂无数据集。去「数据可视化」打包一个。</div>
  </div>
</template>
