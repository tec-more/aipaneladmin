import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

/**
 * 用户侧路由（T7 骨架）
 * A2：独立路由空间，与后台 /panel 完全分离；默认落地 /workflows（节点1 裁定 Q5）。
 * 守卫仅校验 token 存在性（R-03：权限由后端 M8 裁定，前端不复制判断逻辑）。
 */
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/workflows',
    children: [
      {
        path: 'workflows',
        name: 'Workflows',
        component: () => import('@/views/workflows/List.vue'),
        meta: { title: '我的工作流', icon: 'Share' }
      },
      {
        path: 'kb',
        name: 'KnowledgeBase',
        component: () => import('@/views/kb/Index.vue'),
        meta: { title: '知识库', icon: 'Collection' }
      },
      {
        path: 'executions',
        name: 'Executions',
        component: () => import('@/views/executions/Index.vue'),
        meta: { title: '运行记录', icon: 'VideoPlay' }
      },
      {
        path: 'quota',
        name: 'Quota',
        component: () => import('@/views/quota/Index.vue'),
        meta: { title: '配额看板', icon: 'Odometer' }
      },
      {
        path: 'settings/identity',
        name: 'IdentitySettings',
        component: () => import('@/views/settings/Identity.vue'),
        meta: { title: '关联管理', icon: 'Link' }
      }
    ]
  },
  {
    // 工作流编辑器：全屏独立路由（不带 MainLayout 菜单，自带顶栏）
    path: '/workflows/:id/edit',
    name: 'WorkflowEditor',
    component: () => import('@/views/workflows/Editor.vue'),
    meta: { title: '编辑工作流' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/workflows'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局守卫：公开路由白名单 + token 校验 + 回跳
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.public) {
    // 已登录访问登录页 → 回默认落地页
    if (to.name === 'Login' && authStore.isLoggedIn) {
      return next({ path: '/workflows' })
    }
    return next()
  }

  if (!authStore.isLoggedIn) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }
  next()
})

// 标题：产品名由 system store 驱动，路由 meta.title 为前缀
router.afterEach((to) => {
  const base = 'AI Panel'
  document.title = to.meta.title ? `${to.meta.title} - ${base}` : base
})

export default router
