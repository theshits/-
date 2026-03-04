import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '主界面' }
  },
  {
    path: '/sources',
    name: 'Sources',
    component: () => import('@/views/Sources.vue'),
    meta: { title: '排放源管理' }
  },
  {
    path: '/receptors',
    name: 'Receptors',
    component: () => import('@/views/Receptors.vue'),
    meta: { title: '受体点管理' }
  },
  {
    path: '/meteorology',
    name: 'Meteorology',
    component: () => import('@/views/Meteorology.vue'),
    meta: { title: '气象场管理' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || '首页'} - 空气污染扩散模拟平台`
  next()
})

export default router
