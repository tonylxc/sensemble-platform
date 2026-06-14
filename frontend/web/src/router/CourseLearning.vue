<template>
  <div class="course-learning-container">
    <el-container class="learning-layout">
      
      <el-aside width="300px" class="aside-tree">
        <div class="aside-header">
          <h3><i class="el-icon-notebook"></i> 课程知识图谱</h3>
        </div>
        <el-scrollbar>
          <el-tree
            :data="courseTree"
            :props="defaultProps"
            node-key="id"
            highlight-current
            default-expand-all
            @node-click="handleNodeClick"
            class="custom-tree"
          >
            <template #default="{ node, data }">
              <span class="custom-tree-node">
                <i :class="data.children ? 'el-icon-folder' : 'el-icon-document'"></i>
                <span>{{ node.label }}</span>
              </span>
            </template>
          </el-tree>
        </el-scrollbar>
      </el-aside>

      <el-main class="main-content">
        <el-scrollbar v-if="selectedNode && !selectedNode.children">
          <div class="content-section">
            <h1 class="node-title">{{ selectedNode.label }}</h1>
            <el-tag type="success" size="small" class="node-tag">众感 Sensemble 授课内容</el-tag>
            <hr class="divider" />
            
            <div class="markdown-body" v-html="nodeContent.body"></div>
          </div>

          <div class="interaction-section quiz-card" v-if="nodeContent.quizzes && nodeContent.quizzes.length">
            <h3 class="section-title"><i class="el-icon-edit"></i> 思考题巩固</h3>
            
            <div v-for="(quiz, index) in nodeContent.quizzes" :key="quiz.id" class="quiz-item">
              <p class="quiz-question"><strong>Q{{ index + 1 }}：</strong>{{ quiz.question }}</p>
              
              <el-radio-group v-model="quizAnswers[quiz.id]" v-if="quiz.type === 'single'">
                <el-radio v-for="opt in quiz.options" :key="opt.key" :label="opt.key">
                  {{ opt.key }}. {{ opt.value }}
                </el-radio>
              </el-radio-group>
              
              <el-input
                v-else-if="quiz.type === 'text'"
                v-model="quizAnswers[quiz.id]"
                type="textarea"
                :rows="3"
                placeholder="请阐述你的分析..."
              ></el-input>
            </div>
            
            <div class="btn-group">
              <el-button type="primary" :loading="submitLoading" @click="submitQuizzes">提交思考题</el-button>
            </div>
          </div>

          <div class="interaction-section reflection-card">
            <h3 class="section-title"><i class="el-icon-chat-line-round"></i> 实验心得与学术体会</h3>
            <p class="tip-text">请结合本节知识点，简要记录你在虚拟实验操作或 Sensemble 数据分析中的心得感悟（不少于50字）。</p>
            <el-input
              v-model="reflectionText"
              type="textarea"
              :rows="5"
              placeholder="在这里写下你的心得体会..."
              maxlength="500"
              show-word-limit
            ></el-input>
            <div class="btn-group">
              <el-button type="success" :loading="submitLoading" @click="submitReflection">提交心得体会</el-button>
            </div>
          </div>
        </el-scrollbar>

        <el-empty v-else description="请在左侧选择具体知识点开始学习"></el-empty>
      </el-main>

    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

// --- 类型定义 ---
interface TreeNode {
  id: number
  label: string
  children?: TreeNode[]
}

interface QuizOption {
  key: string
  value: string
}

interface Quiz {
  id: number
  type: 'single' | 'text'
  question: string
  options?: QuizOption[]
}

interface NodeContent {
  id: number
  body: string // 富文本 HTML 内容
  quizzes: Quiz[]
}

// --- 响应式状态 ---
const selectedNode = ref<TreeNode | null>(null)
const reflectionText = ref<string>('')
const submitLoading = ref<boolean>(false)
const quizAnswers = reactive<Record<number, any>>({})

// 1. 模拟树状目录数据（未来通过 API 从 FastAPI 调取）
const courseTree = ref<TreeNode[]>([
  {
    id: 1,
    label: '第一章：检测技术基础',
    children: [
      { id: 11, label: '1.1 传感器的静态特性评估' },
      { id: 12, label: '1.2 测量误差分类与边缘去噪处理' }
    ]
  },
  {
    id: 2,
    label: '第二章：物联网与感知数据传输',
    children: [
      { id: 21, label: '2.1 低速传感器 MQTT 报文组装' },
      { id: 22, label: '2.2 边缘侧边缘检测与数据转换流程' }
    ]
  }
])

const defaultProps = {
  children: 'children',
  label: 'label'
}

// 2. 模拟当前选中知识点的详细内容
const nodeContent = reactive<NodeContent>({
  id: 0,
  body: '',
  quizzes: []
})

// --- 核心业务逻辑函数 ---

// 点击左侧知识点树节点
const handleNodeClick = async (data: TreeNode) => {
  if (data.children) return // 点击的是带子目录的章节，不做处理
  
  selectedNode.value = data
  // 重置表单状态
  reflectionText.value = ''
  Object.keys(quizAnswers).forEach(key => delete quizAnswers[Number(key)])
  
  // 模拟从后端 FastAPI 获取数据（这里用假数据模拟接口返回）
  fetchNodeContentFromBackend(data.id)
}

// 模拟 API 请求
const fetchNodeContentFromBackend = (nodeId: number) => {
  nodeContent.id = nodeId
  nodeContent.body = `
    <p>欢迎来到本节微课堂。在<strong>电气测试技术</strong>中，指针仪表的边缘读取往往会因为现场光照、反光造成误差。</p>
    <p>我们采用边缘计算路线（方案 A / 方案 B），将原始图像在边缘端本地通过 <code>OpenCV</code> 的霍夫圆变换和 Canny 算子转换为标准的角度数据，再通过低速物联网通道（HTTP JSON）上传到 <strong>Sensemble 平台</strong>。</p>
    <blockquote>思考：为什么我们要把计算压力推给边缘端，而不是由云端 FastAPI 统一处理？</blockquote>
  `
  nodeContent.quizzes = [
    {
      id: 101,
      type: 'single',
      question: '在低速物联网接入设计中，为了防止耗时的图像识别算法阻塞 FastAPI 主线程，最推荐的架构演进方案是什么？',
      options: [
        { key: 'A', value: '将图像识别压力下推至边缘设备，云端只接收格式化 JSON 数据' },
        { key: 'B', value: '在 FastAPI 主线程中强行同步运行 OpenCV 脚本' },
        { key: 'C', value: '禁止使用图像识别，全部改为人工手录' }
      ]
    },
    {
      id: 102,
      type: 'text',
      question: '请简述方案 A（香橙派 Python）与方案 B（ESP32-CAM C++）在边缘端处理指针仪表数据时的核心区别与适用场景。'
    }
  ]
}

// 提交思考题
const submitQuizzes = () => {
  submitLoading.value = true
  // 模拟发送到后端 `/api/v1/instruction/quiz/submit`
  setTimeout(() => {
    submitLoading.value = false
    console.log('提交的答题数据:', JSON.stringify(quizAnswers))
    ElMessage.success('思考题提交成功，客观题已自动批改！')
  }, 800)
}

// 提交心得体会
const submitReflection = () => {
  if (reflectionText.value.length < 50) {
    ElMessage.warning('为了保证学习效果，心得体会请不要少于 50 字哦。')
    return
  }
  
  submitLoading.value = true
  // 模拟发送到后端 `/api/v1/instruction/reflection/submit`
  setTimeout(() => {
    submitLoading.value = false
    console.log('提交的心得内容:', reflectionText.value)
    ElMessage.success('心得体会提交成功，教师端已同步接收！')
  }, 800)
}
</script>

<style scoped>
.course-learning-container {
  height: calc(100vh - 80px);
  background-color: #0f172a;
  color: #f8fafc;
}
.learning-layout {
  height: 100%;
}
.aside-tree {
  background-color: #1e293b;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
}
.aside-header {
  padding: 20px;
  background-color: #0f172a;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.aside-header h3 {
  margin: 0;
  color: #38bdf8;
  font-size: 16px;
}
.custom-tree {
  background: transparent;
  color: #cbd5e1;
  padding: 10px;
}
:deep(.el-tree-node__content:hover) {
  background-color: rgba(56, 189, 248, 0.1);
}
:deep(.el-tree-node.is-current > .el-tree-node__content) {
  background-color: rgba(74, 222, 128, 0.15) !important;
  color: #4ade80;
}
.main-content {
  background-color: #0f172a;
  padding: 30px 40px;
}
.node-title {
  font-size: 28px;
  color: #ffffff;
  margin-bottom: 10px;
}
.node-tag {
  margin-bottom: 20px;
}
.divider {
  border: 0;
  height: 1px;
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.3), transparent);
  margin-bottom: 25px;
}
.markdown-body {
  font-size: 16px;
  line-height: 1.8;
  color: #cbd5e1;
}
:deep(.markdown-body blockquote) {
  margin: 20px 0;
  padding: 10px 20px;
  background-color: rgba(30, 41, 59, 0.7);
  border-left: 4px solid #38bdf8;
  border-radius: 4px;
}
.interaction-section {
  margin-top: 40px;
  padding: 30px;
  background-color: #1e293b;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}
.section-title {
  margin-top: 0;
  color: #38bdf8;
  font-size: 18px;
  margin-bottom: 20px;
}
.quiz-item {
  margin-bottom: 25px;
  padding-bottom: 20px;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.05);
}
.quiz-question {
  color: #fff;
  font-size: 15px;
  margin-bottom: 15px;
}
:deep(.el-radio) {
  color: #cbd5e1;
  margin-right: 30px;
}
.tip-text {
  font-size: 14px;
  color: #94a3b8;
  margin-bottom: 15px;
}
.btn-group {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
:deep(.el-textarea__inner) {
  background-color: #0f172a;
  border-color: rgba(255, 255, 255, 0.1);
  color: #fff;
}
:deep(.el-textarea__inner:focus) {
  border-color: #4ade80;
}
</style>