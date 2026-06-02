<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter, RouterLink, RouterView } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { notificationApi } from '../api'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const title = computed(() => route.meta.title || '众感 Sensemble')
const isTeacher = computed(() => auth.role === 'teacher' || auth.role === 'admin')
const roleName = computed(() => ({ student: '学生', teacher: '教师', admin: '管理员' }[auth.role] || ''))
const initial = computed(() => ({ student: '学', teacher: '师', admin: '管' }[auth.role] || 'U'))

const notifs = ref([])
const unread = ref(0)
const showNotif = ref(false)
let timer = null

async function loadNotifs() {
  try {
    const { data } = await notificationApi.list()
    notifs.value = data.items
    unread.value = data.unread
  } catch (e) { /* 未登录/后端未起时忽略 */ }
}
async function readOne(n) {
  if (n.is_read) return
  try { await notificationApi.read(n.id); n.is_read = true; unread.value = Math.max(0, unread.value - 1) } catch (e) { /* noop */ }
}
async function readAll() {
  try { await notificationApi.readAll(); notifs.value.forEach(n => (n.is_read = true)); unread.value = 0 } catch (e) { /* noop */ }
}
function toggleNotif() { showNotif.value = !showNotif.value; if (showNotif.value) loadNotifs() }

function logout() { auth.logout(); router.push('/login') }

onMounted(() => { loadNotifs(); timer = setInterval(loadNotifs, 30000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div class="layout">
    <aside class="side">
      <div class="brand">
        <img src="/logo.svg" alt="众感">
        <div style="line-height:1.15"><b>众感</b><br><span>Sensemble</span></div>
      </div>
      <nav class="nav">
        <RouterLink to="/overview" active-class="active"><span class="ic">▦</span>概览</RouterLink>
        <RouterLink to="/devices" active-class="active"><span class="ic">📟</span>我的设备</RouterLink>
        <RouterLink to="/visualize" active-class="active"><span class="ic">📈</span>数据可视化</RouterLink>
        <RouterLink to="/datasets" active-class="active"><span class="ic">🗂️</span>数据集广场</RouterLink>
        <RouterLink v-if="isTeacher" to="/review" active-class="active"><span class="ic">✅</span>审核队列</RouterLink>
        <RouterLink v-if="isTeacher" to="/stats" active-class="active"><span class="ic">📊</span>统计看板</RouterLink>
      </nav>
      <div class="foot">众感汇流，数据共鸣<br>v1.0-MVP</div>
    </aside>

    <main class="main">
      <header class="top">
        <h1>{{ title }}</h1>
        <div class="right">
          <div class="bell" @click="toggleNotif">
            🔔<span v-if="unread > 0" class="badge-dot">{{ unread > 99 ? '99+' : unread }}</span>
            <div v-if="showNotif" class="notif-pop" @click.stop>
              <div class="notif-head"><b>通知</b><a @click="readAll">全部已读</a></div>
              <div class="notif-list">
                <div v-for="n in notifs" :key="n.id" class="notif-item" :class="{ unread: !n.is_read }" @click="readOne(n)">
                  <div class="msg">{{ n.message }}</div>
                  <div class="time">{{ n.created_at ? new Date(n.created_at).toLocaleString() : '' }}</div>
                </div>
                <div v-if="!notifs.length" class="notif-empty">暂无通知</div>
              </div>
            </div>
          </div>
          <div class="chip"><div class="avatar">{{ initial }}</div><span>{{ auth.username }}（{{ roleName }}）</span></div>
          <button class="btn gh sm" @click="logout">退出</button>
        </div>
      </header>
      <section class="content"><RouterView /></section>
    </main>
  </div>
</template>

<style scoped>
.bell { position: relative; cursor: pointer; font-size: 18px; padding: 4px 6px; user-select: none; }
.badge-dot { position: absolute; top: -2px; right: -4px; background: #DB2777; color: #fff; font-size: 10px;
  min-width: 16px; height: 16px; line-height: 16px; text-align: center; border-radius: 999px; padding: 0 4px; font-weight: 700; }
.notif-pop { position: absolute; top: 36px; right: 0; width: 320px; background: #fff; border: 1px solid #e6eaf0;
  border-radius: 12px; box-shadow: 0 14px 40px -12px rgba(15,23,42,.25); z-index: 80; overflow: hidden; }
.notif-head { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-bottom: 1px solid #eef2f6; font-size: 14px; }
.notif-head a { color: #0E8C82; font-size: 12px; cursor: pointer; }
.notif-list { max-height: 360px; overflow: auto; }
.notif-item { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; cursor: pointer; }
.notif-item:hover { background: #f8fafc; }
.notif-item.unread { background: #ecfdf8; }
.notif-item .msg { font-size: 13px; color: #0f172a; line-height: 1.5; }
.notif-item .time { font-size: 11px; color: #94a3b8; margin-top: 4px; }
.notif-empty { padding: 24px; text-align: center; color: #94a3b8; font-size: 13px; }
</style>
