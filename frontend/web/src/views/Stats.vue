<script setup>
import { ref, onMounted } from 'vue'
import { statsApi } from '../api'

const s = ref(null)
const err = ref('')
const stName = { published: '已发布', pending: '待审核', draft: '草稿', rejected: '已退回' }

async function load() {
  try { s.value = (await statsApi.overview()).data }
  catch (e) { err.value = e?.response?.data?.detail || '加载失败（需教师/管理员权限）' }
}
onMounted(load)
</script>

<template>
  <div v-if="err" class="muted">{{ err }}</div>

  <template v-if="s">
    <div class="stats">
      <div class="stat"><div class="n t">{{ s.users }}</div><div class="l">用户数</div></div>
      <div class="stat"><div class="n p">{{ s.devices }}</div><div class="l">设备数</div></div>
      <div class="stat"><div class="n m">{{ s.data_points }}</div><div class="l">累计数据点</div></div>
      <div class="stat"><div class="n i">{{ s.downloads }}</div><div class="l">总下载次数</div></div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>数据集状态分布</h3>
        <table>
          <thead><tr><th>状态</th><th>数量</th></tr></thead>
          <tbody>
            <tr v-for="(c, k) in s.datasets.by_status" :key="k">
              <td><span class="st" :class="k">{{ stName[k] || k }}</span></td><td>{{ c }}</td>
            </tr>
            <tr v-if="!Object.keys(s.datasets.by_status).length"><td colspan="2" class="muted">暂无数据集</td></tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <h3>已发布数据集质量分级（DQS）</h3>
        <table>
          <thead><tr><th>等级</th><th>数量</th></tr></thead>
          <tbody>
            <tr v-for="(c, k) in s.grade_distribution" :key="k">
              <td><span class="badge" :class="k">{{ k }}</span></td><td>{{ c }}</td>
            </tr>
            <tr v-if="!Object.keys(s.grade_distribution).length"><td colspan="2" class="muted">暂无已发布数据集</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </template>
</template>
