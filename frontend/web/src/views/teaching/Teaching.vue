<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { teachingApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/toast'
import katex from 'katex'
import 'katex/dist/katex.min.css'

const auth = useAuthStore()
const isTeacher = computed(() => auth.role === 'teacher' || auth.role === 'admin')
const isAdmin = computed(() => auth.role === 'admin')

// 管理员默认看所有课程，普通用户默认看 EE-TEST-2026
const courseCode = ref(auth.role === 'admin' ? '' : 'EE-TEST-2026')
const tree = ref([])
const sel = ref(null)            // 选中节点详情 {id,title,content,quizzes:[...]}
const answers = ref({})          // quizId -> 作答
const results = ref({})          // quizId -> {is_correct,score}
const reflection = ref('')
const aiQ = ref('')
const aiAns = ref('')
const aiBusy = ref(false)
const aiFb = ref('')
const fbBusy = ref(false)

// 教师弹窗
const showNode = ref(false)
const nodeForm = ref({ id: null, title: '', content: '', parent_id: null })
const showOrganize = ref(false)
const organizeForm = ref({ id: null, title: '', current_parent_id: null, new_parent_id: null })
const showQuiz = ref(false)
const quizForm = ref({ qtype: 'single', stem: '', options: [{ key: 'A', text: '' }, { key: 'B', text: '' }], answer: '', score: 1 })

// 把嵌套树拍平成带层级的列表渲染（避免递归组件）
const flatTree = computed(() => {
  const out = []
  const walk = (nodes, depth) => {
    for (const n of nodes || []) { out.push({ n, depth }); if (n.children?.length) walk(n.children, depth + 1) }
  }
  walk(tree.value, 0)
  return out
})

async function loadTree() {
  try { tree.value = (await teachingApi.nodes(courseCode.value)).data } catch (e) { console.error('加载知识点失败:', e) }
}
async function openNode(id) {
  try {
    sel.value = (await teachingApi.node(id)).data
    answers.value = {}; results.value = {}; reflection.value = ''; aiAns.value = ''; aiFb.value = ''
    // 等 DOM 更新完毕后，异步渲染公式（renderMathAsync 会清除旧标记）
    await nextTick()
    renderMathAsync()
  } catch (e) { toast('加载失败') }
}

// ---- LaTeX 公式渲染（异步，非阻塞） ----
/**
 * 使用 requestIdleCallback 异步渲染 LaTeX 公式（不阻塞主线程）
 * 扫描 .rich 和 .qstem 内的 $...$ 和 $$...$$ 公式，调用 KaTeX 渲染
 */
function renderMathAsync() {
  if ('requestIdleCallback' in window) {
    // 优先级：空闲时执行
    requestIdleCallback(() => {
      renderMath()
    }, { timeout: 2000 })  // 最多等待 2 秒
  } else {
    // 降级：使用 setTimeout（React 中常用做法）
    setTimeout(() => {
      renderMath()
    }, 0)
  }
}

/**
 * 遍历 DOM，查找并渲染 LaTeX 公式
 * 处理流程：
 *   1. 识别 $ 和 $$ 公式（不破坏已渲染内容）
 *   2. 用 KaTeX 转换为 HTML
 *   3. 替换为 <span class="math-..."> 或 <div class="math-display">
 */
function renderMath() {
  // 扫描所有富文本区域
  const richElements = document.querySelectorAll('.rich, .qstem, .aibox')

  richElements.forEach((elem) => {
    try {
      const html = elem.innerHTML

      // 只有当HTML中包含未渲染的公式（$ 或 $$）时才处理
      if (!html.includes('$')) return

      const processed = processLatexInHTML(html)

      if (processed !== html) {
        elem.innerHTML = processed
      }
    } catch (e) {
      console.error('LaTeX 渲染出错:', e)
    }
  })
}

/**
 * 处理 HTML 字符串中的 LaTeX 公式
 * 返回：包含已渲染公式的 HTML 字符串
 */
function processLatexInHTML(html) {
  let result = html

  // 第 1 步：处理 $$ ... $$ 公式（必须先处理，避免被 $ ... $ 搞乱）
  result = result.replace(/\$\$([\s\S]*?)\$\$/g, (match, formula) => {
    try {
      const cleaned = formula.trim()
      if (!cleaned) return match
      const rendered = katex.renderToString(cleaned, {
        throwOnError: false,
        displayMode: true,
      })
      return `<div class="math-display" style="text-align:center;margin:12px 0;overflow-x:auto">${rendered}</div>`
    } catch (e) {
      console.warn('公式渲染失败 (display):', formula, e)
      return match
    }
  })

  // 第 2 步：处理 $ ... $ 公式（行内）
  // 改进的正则：更宽松地匹配 $ 之间的内容
  result = result.replace(/\$([^\$\n]+?)\$/g, (match, formula) => {
    // 跳过空白公式
    if (!formula.trim()) return match

    // 跳过已经是 HTML 的内容
    if (formula.includes('<') || formula.includes('>')) return match

    // 跳过 $$ 模式（在第一步已处理）
    if (formula.includes('$')) return match

    try {
      const rendered = katex.renderToString(formula, {
        throwOnError: false,
        displayMode: false,
      })
      return `<span class="math-inline" style="margin:0 2px">${rendered}</span>`
    } catch (e) {
      console.warn('公式渲染失败 (inline):', formula, e)
      return match  // 保留原文
    }
  })

  return result
}

onMounted(loadTree)

// ---- 答题 ----
function setMulti(qid, key, checked) {
  const s = new Set(answers.value[qid] || [])
  checked ? s.add(key) : s.delete(key)
  answers.value[qid] = [...s]
}
async function submitAnswer(q) {
  const a = answers.value[q.id]
  if (a === undefined || a === '' || (Array.isArray(a) && !a.length)) { toast('请先作答'); return }
  try {
    results.value[q.id] = (await teachingApi.answer(q.id, a)).data
  } catch (e) { toast(e?.response?.data?.detail || '提交失败') }
}
async function submitReflection() {
  if (!reflection.value.trim()) { toast('请输入心得'); return }
  try { await teachingApi.reflection(sel.value.id, reflection.value); toast('心得已提交'); reflection.value = '' }
  catch (e) { toast('提交失败') }
}

// ---- AI 助教 ----
async function askAi() {
  if (!aiQ.value.trim()) return
  aiBusy.value = true; aiAns.value = ''
  try {
    aiAns.value = (await teachingApi.aiAsk(sel.value.id, aiQ.value)).data.answer
    // AI 回答后，异步渲染公式
    await nextTick()
    renderMathAsync()
  }
  catch (e) { aiAns.value = 'AI 调用失败，请稍后再试。' }
  finally { aiBusy.value = false }
}
async function getFeedback() {
  fbBusy.value = true; aiFb.value = ''
  try {
    aiFb.value = (await teachingApi.aiFeedback(sel.value.id)).data.feedback
    // AI 反馈后，异步渲染公式
    await nextTick()
    renderMathAsync()
  }
  catch (e) { aiFb.value = 'AI 调用失败，请稍后再试。' }
  finally { fbBusy.value = false }
}

// ---- 教师：节点 ----
function newRoot() { nodeForm.value = { id: null, title: '', content: '', parent_id: null }; showNode.value = true }
function newChild() { nodeForm.value = { id: null, title: '', content: '', parent_id: sel.value.id }; showNode.value = true }
function editNode() { nodeForm.value = { id: sel.value.id, title: sel.value.title, content: sel.value.content || '', parent_id: sel.value.parent_id }; showNode.value = true }
async function saveNode() {
  if (!nodeForm.value.title.trim()) { toast('请输入标题'); return }
  try {
    if (nodeForm.value.id) await teachingApi.updateNode(nodeForm.value.id, nodeForm.value)
    else await teachingApi.createNode(nodeForm.value)
    showNode.value = false
    await loadTree()
    if (nodeForm.value.id) await openNode(nodeForm.value.id)
    toast('已保存')
  } catch (e) { toast(e?.response?.data?.detail || '保存失败') }
}

// ---- 教师：知识点整理（移动/分组） ----
function organizeNode() {
  organizeForm.value = {
    id: sel.value.id,
    title: sel.value.title,
    current_parent_id: sel.value.parent_id,
    new_parent_id: sel.value.parent_id
  }
  showOrganize.value = true
}
async function moveNode() {
  const form = organizeForm.value
  if (form.new_parent_id === form.id) {
    toast('不能将节点移动到自己下面')
    return
  }
  try {
    await teachingApi.updateNode(form.id, { parent_id: form.new_parent_id })
    showOrganize.value = false
    await loadTree()
    await openNode(form.id)
    toast('已移动')
  } catch (e) {
    toast(e?.response?.data?.detail || '移动失败')
  }
}
// 生成可选的父节点列表（排除当前节点及其子树）
function getAvailableParents() {
  const currentId = organizeForm.value.id
  const flatten = []
  const walk = (nodes) => {
    for (const n of nodes || []) {
      if (n.id !== currentId) flatten.push(n)
      if (n.children?.length) walk(n.children)
    }
  }
  walk(tree.value)
  return flatten
}
async function delNode() {
  if (!confirm('删除该知识点及其子树、思考题与相关记录？此操作不可恢复。')) return
  try { await teachingApi.deleteNode(sel.value.id); sel.value = null; await loadTree(); toast('已删除') }
  catch (e) { toast('删除失败') }
}

// ---- 教师：思考题 ----
function newQuiz() {
  quizForm.value = { qtype: 'single', stem: '', options: [{ key: 'A', text: '' }, { key: 'B', text: '' }], answer: '', score: 1 }
  showQuiz.value = true
}
function addOption() {
  const k = String.fromCharCode(65 + quizForm.value.options.length)
  quizForm.value.options.push({ key: k, text: '' })
}
function toggleAnsMulti(key, checked) {
  const s = new Set(Array.isArray(quizForm.value.answer) ? quizForm.value.answer : [])
  checked ? s.add(key) : s.delete(key)
  quizForm.value.answer = [...s]
}
async function saveQuiz() {
  const f = quizForm.value
  if (!f.stem.trim()) { toast('请输入题干'); return }
  const payload = {
    qtype: f.qtype, stem: f.stem, score: Number(f.score) || 1,
    options: f.qtype === 'short_answer' ? null : f.options,
    answer: f.qtype === 'multiple' ? (Array.isArray(f.answer) ? f.answer : []) : f.answer
  }
  try {
    await teachingApi.addQuiz(sel.value.id, payload)
    showQuiz.value = false
    await openNode(sel.value.id)
    toast('题目已添加')
  } catch (e) { toast(e?.response?.data?.detail || '添加失败') }
}
async function delQuiz(q) {
  if (!confirm('删除该题？')) return
  try { await teachingApi.deleteQuiz(q.id); await openNode(sel.value.id) } catch (e) { toast('删除失败') }
}
const qtypeName = { single: '单选', multiple: '多选', short_answer: '简答' }
</script>

<template>
  <div class="controls">
    <b style="font-size:15px">🎓 教学中心</b>
    <span class="muted small">知识点 → 思考题 → 心得 → AI 助教答疑/反馈</span>
    <select v-model="courseCode" @change="loadTree" style="margin-left:20px">
      <option v-if="isAdmin" value="">📚 全部课程（管理员视图）</option>
      <option value="EE-TEST-2026">EE-TEST-2026 (电气测试 2026)</option>
      <option value="">🔍 其他课程</option>
    </select>
    <button v-if="isTeacher" class="btn pri sm" style="margin-left:auto" @click="newRoot">+ 根知识点</button>
  </div>

  <div class="tlayout">
    <!-- 左：知识点树 -->
    <div class="card tree">
      <h3>知识点</h3>
      <div v-for="{ n, depth } in flatTree" :key="n.id"
           class="tnode" :class="{ on: sel && sel.id === n.id }"
           :style="{ paddingLeft: (depth * 16 + 8) + 'px' }" @click="openNode(n.id)">
        <span class="muted" v-if="depth">└ </span>{{ n.title }}
      </div>
      <div v-if="!flatTree.length" class="muted small" style="padding:8px">
        暂无知识点。{{ isTeacher ? '点右上「+ 根知识点」创建。' : '请教师先创建。' }}
      </div>
    </div>

    <!-- 右：详情 -->
    <div v-if="sel" class="detail">
      <div class="card">
        <h3>
          {{ sel.title }}
          <span v-if="isTeacher" style="display:flex;gap:6px">
            <button class="btn gh sm" @click="newChild">+ 子知识点</button>
            <button class="btn gh sm" @click="editNode">编辑</button>
            <button class="btn gh sm" @click="organizeNode">🔗 整理</button>
            <button class="btn gh sm" @click="newQuiz">+ 思考题</button>
            <button class="btn no sm" @click="delNode">删除</button>
          </span>
        </h3>
        <!-- 富文本内容（教师编写，HTML 渲染） -->
        <div v-if="sel.content" class="rich" v-html="sel.content"></div>
        <div v-else class="muted small">（本知识点暂无内容）</div>
      </div>

      <!-- 思考题 -->
      <div class="card">
        <h3>思考题 <span class="muted small">{{ sel.quizzes.length }} 题</span></h3>
        <div v-for="(q, i) in sel.quizzes" :key="q.id" class="quiz">
          <div class="qstem"><span class="badge B">{{ qtypeName[q.qtype] }}</span> {{ i + 1 }}. {{ q.stem }}
            <button v-if="isTeacher" class="btn no sm" style="float:right" @click="delQuiz(q)">删</button>
          </div>
          <div v-if="q.qtype !== 'short_answer'" class="opts">
            <label v-for="o in q.options" :key="o.key" class="opt">
              <input v-if="q.qtype === 'single'" type="radio" :name="'q' + q.id" :value="o.key" v-model="answers[q.id]">
              <input v-else type="checkbox" :value="o.key" :checked="(answers[q.id] || []).includes(o.key)"
                     @change="setMulti(q.id, o.key, $event.target.checked)">
              {{ o.key }}. {{ o.text }}
            </label>
          </div>
          <textarea v-else v-model="answers[q.id]" rows="2" placeholder="输入你的答案" style="width:100%"></textarea>
          <div class="row">
            <button class="btn pri sm" @click="submitAnswer(q)">提交</button>
            <span v-if="results[q.id]" class="rst">
              <template v-if="results[q.id].is_correct === true">✅ 正确 +{{ results[q.id].score }}</template>
              <template v-else-if="results[q.id].is_correct === false">❌ 答错</template>
              <template v-else>📝 已提交（简答待教师评阅）</template>
            </span>
            <span v-if="isTeacher && q.answer !== undefined" class="muted small">参考答案：{{ Array.isArray(q.answer) ? q.answer.join(',') : q.answer }}</span>
          </div>
        </div>
        <div v-if="!sel.quizzes.length" class="muted small">本知识点暂无思考题。</div>
      </div>

      <!-- 心得体会 -->
      <div class="card">
        <h3>我的心得体会</h3>
        <textarea v-model="reflection" rows="3" placeholder="写下你对本知识点的理解、疑问或实验体会…" style="width:100%"></textarea>
        <div class="row"><button class="btn pri sm" @click="submitReflection">提交心得</button></div>
      </div>

      <!-- AI 助教 -->
      <div class="card ai">
        <h3>🤖 AI 助教</h3>
        <p class="muted small">就本知识点提问，或让 AI 点评你的学习过程（基于你的心得与答题）。</p>
        <div class="row" style="gap:8px">
          <input v-model="aiQ" placeholder="例如：塞贝克效应和帕尔贴效应有什么区别？" style="flex:1" @keyup.enter="askAi">
          <button class="btn pri sm" :disabled="aiBusy" @click="askAi">{{ aiBusy ? '思考中…' : '提问' }}</button>
        </div>
        <div v-if="aiAns" class="aibox">{{ aiAns }}</div>

        <div class="row" style="margin-top:12px">
          <button class="btn gh sm" :disabled="fbBusy" @click="getFeedback">{{ fbBusy ? '生成中…' : '✨ 让 AI 点评我的学习' }}</button>
        </div>
        <div v-if="aiFb" class="aibox fb">{{ aiFb }}</div>
      </div>
    </div>

    <div v-else class="card muted" style="display:grid;place-items:center;min-height:200px">
      ← 从左侧选择一个知识点开始学习
    </div>
  </div>

  <!-- 教师：节点编辑弹窗 -->
  <div class="mask" v-if="showNode" @click.self="showNode = false">
    <div class="modal">
      <h3>{{ nodeForm.id ? '编辑知识点' : (nodeForm.parent_id ? '新建子知识点' : '新建根知识点') }}</h3>
      <label>标题</label><input v-model="nodeForm.title" style="width:100%">
      <label>内容（支持 HTML 富文本）</label>
      <textarea v-model="nodeForm.content" rows="8" placeholder="<h4>原理</h4><p>……</p>" style="width:100%"></textarea>
      <div class="acts">
        <button class="btn gh" @click="showNode = false">取消</button>
        <button class="btn pri" @click="saveNode">保存</button>
      </div>
    </div>
  </div>

  <!-- 教师：知识点整理弹窗 -->
  <div class="mask" v-if="showOrganize" @click.self="showOrganize = false">
    <div class="modal">
      <h3>整理知识点：{{ organizeForm.title }}</h3>
      <label>当前所属：<b>{{ organizeForm.current_parent_id ? tree.find(n => n.id === organizeForm.current_parent_id)?.title || '？' : '（顶级）' }}</b></label>
      <label>移动到：</label>
      <select v-model.number="organizeForm.new_parent_id" style="width:100%">
        <option :value="null">（顶级）</option>
        <optgroup v-for="parent in getAvailableParents().filter(n => !n.parent_id)" :label="parent.title" :key="parent.id">
          <option :value="parent.id">└ {{ parent.title }}</option>
          <option v-for="child in getAvailableParents().filter(n => n.parent_id === parent.id)" :key="child.id" :value="child.id">
            └─ {{ child.title }}
          </option>
        </optgroup>
      </select>
      <p class="muted small" style="margin-top:12px;font-size:12px">💡 选择新的父知识点，或「顶级」来独立化它</p>
      <div class="acts">
        <button class="btn gh" @click="showOrganize = false">取消</button>
        <button class="btn pri" @click="moveNode">确定移动</button>
      </div>
    </div>
  </div>

  <!-- 教师：加思考题弹窗 -->
  <div class="mask" v-if="showQuiz" @click.self="showQuiz = false">
    <div class="modal">
      <h3>新增思考题</h3>
      <label>题型</label>
      <select v-model="quizForm.qtype" style="width:100%">
        <option value="single">单选</option>
        <option value="multiple">多选</option>
        <option value="short_answer">简答</option>
      </select>
      <label>题干</label><textarea v-model="quizForm.stem" rows="2" style="width:100%"></textarea>
      <template v-if="quizForm.qtype !== 'short_answer'">
        <label>选项</label>
        <div v-for="o in quizForm.options" :key="o.key" class="row" style="gap:6px;margin:4px 0">
          <b style="width:18px">{{ o.key }}</b><input v-model="o.text" placeholder="选项内容" style="flex:1">
          <template v-if="quizForm.qtype === 'single'">
            <label class="muted small"><input type="radio" :value="o.key" v-model="quizForm.answer"> 正确</label>
          </template>
          <template v-else>
            <label class="muted small"><input type="checkbox" :checked="(quizForm.answer || []).includes(o.key)"
                    @change="toggleAnsMulti(o.key, $event.target.checked)"> 正确</label>
          </template>
        </div>
        <button class="btn gh sm" @click="addOption">+ 选项</button>
      </template>
      <template v-else>
        <label>参考答案（要点，供教师评阅）</label>
        <textarea v-model="quizForm.answer" rows="2" style="width:100%"></textarea>
      </template>
      <label>分值</label><input v-model.number="quizForm.score" type="number" style="width:100%">
      <div class="acts">
        <button class="btn gh" @click="showQuiz = false">取消</button>
        <button class="btn pri" @click="saveQuiz">添加</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tlayout { display: grid; grid-template-columns: 280px 1fr; gap: 16px; align-items: start; }
.tree { max-height: calc(100vh - 160px); overflow: auto; }
.tnode { padding: 7px 8px; border-radius: 8px; cursor: pointer; font-size: 13.5px; line-height: 1.5; }
.tnode:hover { background: #f1f5f9; }
.tnode.on { background: linear-gradient(90deg, rgba(14,140,130,.14), rgba(124,58,237,.10)); font-weight: 600; }
.detail { display: flex; flex-direction: column; gap: 16px; }
.rich { font-size: 14px; line-height: 1.8; color: #0f172a; }
.rich :deep(img) { max-width: 100%; }
.rich :deep(.math-display) { margin: 12px 0 !important; text-align: center; overflow-x: auto; }
.rich :deep(.math-inline) { margin: 0 2px; }
.quiz { border: 1px solid var(--line); border-radius: 12px; padding: 12px; margin-bottom: 10px; }
.qstem { font-size: 14px; margin-bottom: 8px; }
.qstem :deep(.math-inline) { margin: 0 2px; }
.opts { display: flex; flex-direction: column; gap: 6px; margin: 6px 0; }
.opt { font-size: 13.5px; cursor: pointer; }
.opt input { margin-right: 6px; }
.quiz .row { display: flex; align-items: center; gap: 12px; margin-top: 8px; }
.rst { font-size: 13px; font-weight: 600; }
.ai { background: linear-gradient(180deg, #f8fafc, #fff); }
.aibox { white-space: pre-wrap; background: #0B1220; color: #d8e1ec; border-radius: 10px; padding: 12px 14px;
  font-size: 13.5px; line-height: 1.7; margin-top: 10px; }
.aibox.fb { background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }
.aibox :deep(.math-display) { background: #fff; color: #000; border-radius: 6px; padding: 10px; margin: 10px 0; }
.aibox :deep(.math-inline) { color: #d8e1ec; margin: 0 2px; }
</style>
