<script setup>
import { ref, computed, onMounted } from 'vue'
import { keyApi } from '../api'
import { toast } from '../toast'

const keys = ref([])
const showModal = ref(false)
const name = ref('')
const created = ref(null)   // 创建成功后的 {id, name, api_key, note}
const saving = ref(false)

const apiUrl = computed(() => `${location.origin}/api/v1/open/datasets`)
const curlExample = computed(() => `curl -H "X-API-Key: <你的密钥>" ${apiUrl.value}`)

async function load() {
  try { keys.value = (await keyApi.list()).data } catch (e) { /* 后端未起 */ }
}
function openModal() {
  name.value = ''
  created.value = null
  showModal.value = true
}
async function create() {
  saving.value = true
  try {
    const { data } = await keyApi.create(name.value || 'default')
    created.value = data
    await load()
    toast('密钥已创建，请立即复制保存')
  } catch (e) {
    toast(e?.response?.data?.detail || '创建失败')
  } finally { saving.value = false }
}
async function copy(text) {
  try { await navigator.clipboard.writeText(text); toast('已复制到剪贴板') }
  catch (e) { toast('复制失败，请手动选择文本') }
}
async function revoke(k) {
  if (!confirm(`确定吊销密钥「${k.name}」？使用此密钥的脚本将立即失效。`)) return
  try { await keyApi.revoke(k.id); toast('已吊销'); await load() }
  catch (e) { toast(e?.response?.data?.detail || '吊销失败') }
}
onMounted(load)
</script>

<template>
  <div class="card">
    <h3>API 密钥 <button class="btn pri sm" @click="openModal">+ 新建密钥</button></h3>
    <p class="muted small" style="margin:-6px 0 12px">
      供第三方脚本/程序以只读方式访问<b>开放数据集</b>（公开且已发布），请求头携带 <code>X-API-Key</code>。密钥仅在创建时显示一次。
    </p>
    <table>
      <thead><tr><th>名称</th><th>创建时间</th><th>最后使用</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="k in keys" :key="k.id">
          <td><b>{{ k.name }}</b></td>
          <td>{{ k.created_at ? new Date(k.created_at).toLocaleString() : '-' }}</td>
          <td>{{ k.last_used ? new Date(k.last_used).toLocaleString() : '从未使用' }}</td>
          <td><button class="btn no sm" @click="revoke(k)">吊销</button></td>
        </tr>
        <tr v-if="!keys.length"><td colspan="4" class="muted">还没有密钥。点右上「新建密钥」生成一个。</td></tr>
      </tbody>
    </table>
  </div>

  <div class="card">
    <h3>如何使用</h3>
    <p class="muted small">在请求头加入密钥即可调用开放 API（无需登录）：</p>
    <div class="tokenbox" style="margin:6px 0 10px">{{ curlExample }}</div>
    <p class="muted small">
      可用端点：<code>GET /api/v1/open/datasets</code>（列表）、
      <code>GET /api/v1/open/datasets/{id}/download</code>（下载 CSV/JSON）。
    </p>
    <button class="btn gh sm" @click="copy(curlExample)">复制示例</button>
  </div>

  <div class="mask" v-if="showModal" @click.self="showModal = false">
    <div class="modal">
      <h3>新建 API 密钥</h3>
      <template v-if="!created">
        <p class="muted small">为密钥起一个便于识别的名称（如用途或项目名）。</p>
        <label>名称</label>
        <input v-model="name" placeholder="如 课程脚本 / 实验室爬虫" style="width:100%" @keyup.enter="create">
      </template>
      <template v-else>
        <p class="muted small">密钥仅此一次完整显示，请立即复制保存；关闭后无法再次查看。</p>
        <label>API Key（{{ created.name }}）</label>
        <div class="tokenbox">{{ created.api_key }}</div>
      </template>
      <div class="acts">
        <button class="btn gh" @click="showModal = false">{{ created ? '完成' : '取消' }}</button>
        <button v-if="!created" class="btn pri" :disabled="saving" @click="create">生成密钥</button>
        <button v-else class="btn pri" @click="copy(created.api_key)">复制密钥</button>
      </div>
    </div>
  </div>
</template>
