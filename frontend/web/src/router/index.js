import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppLayout from '../components/AppLayout.vue'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', redirect: '/overview' },
      { path: 'overview', component: () => import('../views/Overview.vue'), meta: { title: '概览' } },
      { path: 'devices', component: () => import('../views/Devices.vue'), meta: { title: '我的设备' } },
      { path: 'visualize', component: () => import('../views/Visualize.vue'), meta: { title: '数据可视化' } },
      { path: 'datasets', component: () => import('../views/Datasets.vue'), meta: { title: '数据集广场' } },
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
