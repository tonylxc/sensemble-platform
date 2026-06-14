<template>
  <div class="teaching-container">
    <div class="teaching-header">
      <h1>教学中心</h1>
      <select v-model="selectedCourse" class="course-select">
        <option value="">选择课程...</option>
        <option value="EE-TEST-2026">EE-TEST-2026 (电气测试)</option>
      </select>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else class="teaching-content">
      <div class="knowledge-tree">
        <div
          v-for="node in nodes"
          :key="node.id"
          class="knowledge-node"
          @click="selectedNode = node"
          :class="{ active: selectedNode?.id === node.id }"
        >
          <div class="node-title">{{ node.title }}</div>
        </div>
      </div>

      <div class="knowledge-detail">
        <div v-if="!selectedNode" class="no-selection">选择左边的知识点查看内容</div>
        <div v-else class="node-content">
          <h2>{{ selectedNode.title }}</h2>
          <div class="rich" v-html="selectedNode.content"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const selectedCourse = ref('EE-TEST-2026')
const selectedNode = ref(null)
const nodes = ref([])
const loading = ref(false)
const error = ref('')

onMounted(() => {
  loadNodes()
})

const loadNodes = async () => {
  if (!selectedCourse.value) {
    nodes.value = []
    return
  }

  loading.value = true
  error.value = ''
  try {
    const token = localStorage.getItem('access_token')
    if (!token) {
      error.value = '请先登录'
      return
    }

    const res = await fetch(
      `http://localhost:8000/api/v1/teaching/nodes?course_code=${selectedCourse.value}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    )

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }

    nodes.value = await res.json()
    selectedNode.value = nodes.value[0] || null

    // 在下一帧执行 KaTeX 渲染
    await new Promise(resolve => requestAnimationFrame(resolve))
    renderMath()
  } catch (err) {
    error.value = `加载失败: ${err.message}`
    console.error('Load teaching nodes error:', err)
  } finally {
    loading.value = false
  }
}

const renderMath = () => {
  // 触发 KaTeX 渲染
  const container = document.querySelector('.knowledge-detail')
  if (!container || typeof window.katex === 'undefined') {
    console.warn('KaTeX not available')
    return
  }

  // 查找所有需要渲染的元素
  const elements = container.querySelectorAll('.rich')
  elements.forEach(el => {
    const html = el.innerHTML
    if (!html) return

    // 正则表达式匹配 $ ... $ 和 $$ ... $$
    let rendered = html

    // 显示公式：$$ ... $$（必须先处理，否则会与行内公式冲突）
    rendered = rendered.replace(/\$\$([\s\S]*?)\$\$/g, (match, content) => {
      try {
        const result = window.katex.renderToString(content, {
          displayMode: true,
          throwOnError: false
        })
        return `<div class="katex-display">${result}</div>`
      } catch (e) {
        console.error('KaTeX render error:', e, content)
        return match
      }
    })

    // 行内公式：$ ... $
    rendered = rendered.replace(/\$(.*?)\$/g, (match, content) => {
      if (!content.trim()) return match
      try {
        const result = window.katex.renderToString(content, {
          displayMode: false,
          throwOnError: false
        })
        return `<span class="katex-inline">${result}</span>`
      } catch (e) {
        console.error('KaTeX render error:', e, content)
        return match
      }
    })

    el.innerHTML = rendered
  })
}

// 监听课程变化
const handleCourseChange = () => {
  loadNodes()
}
</script>

<style scoped>
.teaching-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
}

.teaching-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.teaching-header h1 {
  margin: 0;
  font-size: 28px;
  color: #333;
}

.course-select {
  padding: 8px 12px;
  font-size: 14px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
}

.teaching-content {
  display: flex;
  gap: 20px;
  flex: 1;
}

.knowledge-tree {
  width: 300px;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow-y: auto;
  padding: 10px 0;
  background: #f9f9f9;
}

.knowledge-node {
  padding: 12px 16px;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: all 0.2s;
}

.knowledge-node:hover {
  background: #f0f0f0;
}

.knowledge-node.active {
  background: #e3f2fd;
  border-left-color: #1976d2;
  color: #1976d2;
}

.node-title {
  font-weight: 500;
  font-size: 14px;
}

.knowledge-detail {
  flex: 1;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 20px;
  overflow-y: auto;
  background: white;
}

.no-selection {
  color: #999;
  text-align: center;
  padding: 40px 20px;
}

.node-content h2 {
  margin-top: 0;
  color: #333;
}

.rich {
  line-height: 1.8;
  font-size: 16px;
  color: #333;
}

.loading,
.error {
  padding: 20px;
  text-align: center;
  font-size: 16px;
}

.error {
  color: #d32f2f;
  background: #ffebee;
  border-radius: 4px;
}

/* KaTeX 样式 */
:deep(.katex) {
  font-size: 1.1em;
}

:deep(.katex-display) {
  display: block;
  margin: 1em 0;
  padding: 10px;
  background: #f5f5f5;
  border-left: 3px solid #1976d2;
}

:deep(.katex-inline) {
  display: inline;
}

/* 确保公式清晰显示 */
:deep(.katex-mathml) {
  display: none;
}
</style>
