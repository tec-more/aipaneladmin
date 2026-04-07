import { createRouter, createWebHistory } from 'vue-router'
import { useMenuStore } from '@/stores/menu'

const routes = [
  // 主页：笑话面对面介绍页面
  {
    path: '/',
    name: 'LandingPage',
    component: () => import('@/views/LandingPage.vue'),
    meta: { title: '笑话面对面', public: true }
  },
  // 管理后台登录
  {
    path: '/panel',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { title: '管理后台登录', public: true }
  },
  // 管理后台主界面
  {
    path: '/panel',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/panel/dashboard',
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
      },
      {
        path: 'customer',
        name: 'Customer',
        redirect: 'customer/list',
        meta: { title: '客户管理', icon: 'User' }
      },
      {
        path: 'customer/list',
        name: 'CustomerList',
        component: () => import('@/views/customer/Index.vue'),
        meta: { title: '客户列表' }
      },
      {
        path: 'customer/create',
        name: 'CustomerCreate',
        component: () => import('@/views/customer/Edit.vue'),
        meta: { title: '新增客户' }
      },
      {
        path: 'customer/edit/:id',
        name: 'CustomerEdit',
        component: () => import('@/views/customer/Edit.vue'),
        meta: { title: '编辑客户' }
      },
      {
        path: 'customer/detail/:id',
        name: 'CustomerDetail',
        component: () => import('@/views/customer/Detail.vue'),
        meta: { title: '客户详情' }
      },
      {
        path: 'customer/membership-levels',
        name: 'MembershipLevels',
        component: () => import('@/views/customer/membership-levels/index.vue'),
        meta: { title: '会员等级配置' }
      },
      {
        path: 'customer/orders',
        name: 'CustomerOrders',
        component: () => import('@/views/customer/orders/index.vue'),
        meta: { title: '订单管理' }
      },
      {
        path: 'customer/payments',
        name: 'CustomerPayments',
        component: () => import('@/views/customer/payments/index.vue'),
        meta: { title: '支付记录' }
      },
      {
        path: 'customer/usage',
        name: 'CustomerUsage',
        component: () => import('@/views/customer/usage/index.vue'),
        meta: { title: '使用记录' }
      },
      {
        path: 'product',
        name: 'Product',
        component: () => import('@/views/product/Index.vue'),
        meta: { title: '产品管理', icon: 'Box' }
      },
      {
        path: 'product/:id',
        name: 'ProductDetail',
        component: () => import('@/views/product/Detail.vue'),
        meta: { title: '产品详情' }
      },
      {
        path: 'order',
        name: 'Order',
        component: () => import('@/views/order/Index.vue'),
        meta: { title: '订单管理', icon: 'Document' }
      },
      {
        path: 'order/:id',
        name: 'OrderDetail',
        component: () => import('@/views/order/Detail.vue'),
        meta: { title: '订单详情' }
      },
      // LLM大模型管理
      {
        path: 'llm/models',
        name: 'LLMModels',
        component: () => import('@/views/llm/models/index.vue'),
        meta: { title: '模型管理', icon: 'Management' }
      },
      {
        path: 'llm/api-keys',
        name: 'LLMApiKeys',
        component: () => import('@/views/llm/api-keys/index.vue'),
        meta: { title: 'API密钥', icon: 'Key' }
      },
      {
        path: 'llm/conversations',
        name: 'LLMConversations',
        component: () => import('@/views/llm/conversations/index.vue'),
        meta: { title: '对话记录', icon: 'ChatDotRound' }
      },
      {
        path: 'llm/usage',
        name: 'LLMUsage',
        component: () => import('@/views/llm/usage/index.vue'),
        meta: { title: '使用统计', icon: 'DataAnalysis' }
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
  document.title = `${to.meta.title || ''} - 笑话面对面`

  // 直接从 localStorage 读取 token 判断登录状态
  const token = localStorage.getItem('token')
  const isLoggedIn = !!token

  // 已登录用户访问登录页，直接跳转到后台首页
  if (to.path === '/panel' && isLoggedIn) {
    next({ path: '/panel/dashboard' })
    return
  }

  if (to.meta.public) {
    next()
  } else if (!isLoggedIn) {
    next({ path: '/panel', query: { redirect: to.fullPath } })
  } else {
    // 已登录，加载用户菜单并添加动态路由
    const menuStore = useMenuStore()
    if (!menuStore.isLoaded && !menuStore.loading) {
      try {
        await menuStore.fetchUserMenus()

        // 添加动态路由到 router
        const dynamicRoutes = menuStore.generateRoutes()
        dynamicRoutes.forEach(route => {
          // 查找 /panel 的子路由位置
          const panelRoute = router.resolve('/panel')
          if (panelRoute && panelRoute.route.value && panelRoute.route.value.children) {
            // 添加到已有子路由中
            router.addRoute('/panel', route)
          } else {
            // 直接添加
            router.addRoute('panel', route)
          }
        })
      } catch (error) {
        console.error('加载菜单失败:', error)
      }
    }
    next()
  }
})

export default router
