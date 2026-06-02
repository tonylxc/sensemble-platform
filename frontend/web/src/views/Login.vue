<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const tab = ref('login')
const username = ref('')
const password = ref('')
const role = ref('student')
const err = ref('')
const loading = ref(false)

async function submit() {
  err.value = ''
  loading.value = true
  try {
    if (tab.value === 'login') await auth.login(username.value, password.value)
    else await auth.register({ username: username.value, password: password.value, role: role.value })
    router.push('/overview')
  } catch (e) {
    err.value = e?.response?.data?.detail || e?.response?.data?.message || '操作失败，请确认后端已启动（:8000）'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <div class="hero">
      <img src="/logo.svg" alt="">
      <h1>众感 Sensemble</h1>
      <p>开放感知数据平台 · 师生上传真实感知数据，服务实验教学、科研交流与工程实践。</p>
      <div class="slogan">众感汇流，数据共鸣 · Every sensor, one ensemble.</div>
    </div>
    <div class="panel">
      <div class="form">
        <h2>{{ tab === 'login' ? '登录' : '注册' }}</h2>
        <p class="muted small">默认管理员 admin / admin123，或直接注册新账号</p>
        <div class="tabs">
          <button :class="{ on: tab === 'login' }" @click="tab = 'login'">登录</button>
          <button :class="{ on: tab === 'register' }" @click="tab = 'register'">注册</button>
        </div>
        <label>用户名 / 学号</label>
        <input v-model="username" placeholder="如 stud1" @keyup.enter="submit">
        <label>密码</label>
        <input v-model="password" type="password" placeholder="••••••" @keyup.enter="submit">
        <template v-if="tab === 'register'">
          <label>角色</label>
          <select v-model="role">
            <option value="student">学生</option>
            <option value="teacher">教师</option>
          </select>
        </template>
        <div class="err">{{ err }}</div>
        <button class="btn pri" style="width:100%" :disabled="loading" @click="submit">
          {{ loading ? '处理中…' : (tab === 'login' ? '登录' : '注册并登录') }}
        </button>
      </div>
    </div>
  </div>
</template>
