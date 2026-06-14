import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppLayout from '../components/AppLayout.vue'

// 核心页面同步导入：避免懒加载 chunk 在生产 nginx 缓存里"老旧不一致"的问题
// (登录/大屏/数据集/审核/统计相对独立，保留懒加载以减小初次包)
import Overview from '../views/Overview.vue'
import Devices from '../views/Devices.vue'
import Visualize from '../views/Visualize.vue'
import Keys from '../views/Keys.vue'
import Help from '../views/Help.vue'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true } },
  // 实验室大屏：顶层全屏路由（不套 AppLayout 侧栏），教师/管理员可见
  { path: '/dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '实验室大屏', roles: ['teacher', 'admin'] } },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', redirect: '/overview' },
      { path: 'overview', component: Overview, meta: { title: '概览' } },
      { path: 'devices', component: Devices, meta: { title: '我的设备' } },
      { path: 'visualize', component: Visualize, meta: { title: '数据可视化' } },
      { path: 'datasets', component: () => import('../views/Datasets.vue'), meta: { title: '数据集广场' } },
      { path: 'keys', component: Keys, meta: { title: 'API 密钥' } },
      { path: 'help', component: Help, meta: { title: '使用帮助' } },
      { path: 'teaching', component: () => import('@/views/teaching/Teaching.vue'), meta: { title: '教学中心' } },
      // /course/learning 与 /teaching 同页；懒加载指向 views/teaching/Teaching.vue
      { path: 'course/learning', name: 'Teaching', component: () => import('@/views/teaching/Teaching.vue'), meta: { title: '课程学习' } },
      { path: 'review', component: () => import('../views/Review.vue'), meta: { title: '审核队列', roles: ['teacher', 'admin'] } },
      { path: 'stats', component: () => import('../views/Stats.vue'), meta: { title: '统计看板', roles: ['teacher', 'admin'] } }
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthed()) return '/login'
  if (to.meta.roles && !to.meta.roles.includes(auth.role)) return '/overview'
  if (to.path === '/login' && auth.isAuthed()) return '/overview'
  return true
})

export default router
