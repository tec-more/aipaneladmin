import { createRouter, createWebHistory } from 'vue-router'
import { useMenuStore } from '@/stores/menu'

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
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Index.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/user/Index.vue'),
        meta: { title: '用户管理', icon: 'User' }
      },
      {
        path: 'departments',
        name: 'Departments',
        component: () => import('@/views/department/Index.vue'),
        meta: { title: '部门管理', icon: 'OfficeBuilding' }
      },
      {
        path: 'roles',
        name: 'Roles',
        component: () => import('@/views/role/Index.vue'),
        meta: { title: '角色管理', icon: 'UserFilled' }
      },
      {
        path: 'permissions',
        name: 'Permissions',
        component: () => import('@/views/permission/Index.vue'),
        meta: { title: '权限管理', icon: 'Key' }
      },
      {
        path: 'menus',
        name: 'Menus',
        component: () => import('@/views/menu/Index.vue'),
        meta: { title: '菜单管理', icon: 'Menu' }
      },
      {
        path: 'plugins',
        name: 'Plugins',
        component: () => import('@/views/plugin/Index.vue'),
        meta: { title: '插件管理', icon: 'Connection' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '404', public: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  document.title = `${to.meta.title || ''} - AI Panel Admin`

  // 直接从 localStorage 读取 token 判断登录状态
  const token = localStorage.getItem('token')
  const isLoggedIn = !!token

  // 已登录用户访问登录页，直接跳转到首页
  if (to.path === '/login' && isLoggedIn) {
    next({ path: '/' })
    return
  }

  if (to.meta.public) {
    next()
  } else if (!isLoggedIn) {
    next({ path: '/login', query: { redirect: to.fullPath } })
  } else {
    // 已登录，加载用户菜单
    const menuStore = useMenuStore()
    if (!menuStore.isLoaded && !menuStore.loading) {
      try {
        await menuStore.fetchUserMenus()
      } catch (error) {
        console.error('加载菜单失败:', error)
      }
    }
    next()
  }
})

export default router
