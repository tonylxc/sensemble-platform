<script setup>
import { ref, onMounted } from 'vue'
import { datasetApi } from '../api'
import { toast } from '../toast'

const list = ref([])

async function load() {
  try { list.value = (await datasetApi.pending()).data } catch (e) { /* 后端未起 */ }
}
async function act(d, result) {
  let comment = ''
  if (result === 'rejected') comment = prompt('退回意见（可空）：') || ''
  try {
    await datasetApi.review(d.dataset_id, { result, comment })
    toast(result === 'approved' ? '已通过并发布' : '已退回')
    await load()
  } catch (e) { toast(e?.response?.data?.detail || '操作失败') }
}
onMounted(load)
</script>

<template>
  <div class="card">
    <h3>待审核数据集（教师 / 管理员 · FR-10.1）</h3>
    <table>
      <thead><tr><th>编号</th><th>名称</th><th>DQS</th><th>设备</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="d in list" :key="d.dataset_id">
          <td>{{ d.dataset_id }}</td>
          <td>{{ d.name }}</td>
          <td><span class="badge" :class="d.grade">{{ d.grade }} · {{ d.dqs }}</span></td>
          <td>{{ d.device_id }}</td>
          <td style="display:flex;gap:6px">
            <button class="btn ok sm" @click="act(d, 'approved')">通过</button>
            <button class="btn no sm" @click="act(d, 'rejected')">退回</button>
          </td>
        </tr>
        <tr v-if="!list.length"><td colspan="5" class="muted">审核队列为空 🎉</td></tr>
      </tbody>
    </table>
  </div>
</template>
