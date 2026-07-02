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
    name: 'panel',
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
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/user/Profile.vue'),
        meta: { title: '个人信息', hidden: true }
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
        path: 'system-setting',
        name: 'SystemSetting',
        component: () => import('@/views/systemSetting/Index.vue'),
        meta: { title: '系统设置', icon: 'Setting' }
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
      { path: 'order/:id', name: 'OrderDetail', component: () => import('@/views/order/Detail.vue'), meta: { title: '订单详情' } },
      // 第三方平台管理
      { path: 'thirdparty', name: 'ThirdParty', redirect: 'thirdparty/platforms', meta: { title: '第三方平台', icon: 'CloudServer' } },
      { path: 'thirdparty/platforms', name: 'ThirdPartyPlatforms', component: () => import('@/views/thirdparty/platforms/index.vue'), meta: { title: '平台管理', icon: 'Setting' } },
      { path: 'thirdparty/agents', name: 'ThirdPartyAgents', component: () => import('@/views/thirdparty/agents/index.vue'), meta: { title: '智能体管理', icon: 'Bot' } },
      // LLM大模型管理
      { path: 'llm/models', name: 'LLMModels', component: () => import('@/views/llm/models/index.vue'), meta: { title: '模型管理', icon: 'Management' } },
      { path: 'llm/api-keys', name: 'LLMApiKeys', component: () => import('@/views/llm/api-keys/index.vue'), meta: { title: 'API密钥', icon: 'Key' } },
      { path: 'llm/usage', name: 'LLMUsage', component: () => import('@/views/llm/usage/index.vue'), meta: { title: '使用记录', icon: 'DataAnalysis' } },
      // 智能体管理
      { path: 'agent/list', name: 'AgentList', component: () => import('@/views/agent/agents/index.vue'), meta: { title: '智能体' } },
      { path: 'agent/graph/:id', name: 'AgentGraph', component: () => import('@/views/agent/agents/graph.vue'), meta: { title: '智能体结构图' } },
      { path: 'agent/create', name: 'AgentCreate', component: () => import('@/views/agent/agents/edit.vue'), meta: { title: '创建智能体' } },
      { path: 'agent/edit/:id', name: 'AgentEdit', component: () => import('@/views/agent/agents/edit.vue'), meta: { title: '编辑智能体' } },
      { path: 'agent/skills', name: 'AgentSkills', component: () => import('@/views/agent/skills/index.vue'), meta: { title: '技能管理' } },
      { path: 'agent/skills/create', name: 'SkillCreate', component: () => import('@/views/agent/skills/edit.vue'), meta: { title: '创建技能' } },
      { path: 'agent/skills/edit/:id', name: 'SkillEdit', component: () => import('@/views/agent/skills/edit.vue'), meta: { title: '编辑技能' } },
      { path: 'agent/skills/category', name: 'SkillCategory', component: () => import('@/views/agent/skills/category.vue'), meta: { title: '技能分类管理' } },
      { path: 'agent/tools', name: 'AgentTools', component: () => import('@/views/agent/tools/index.vue'), meta: { title: '工具管理' } },
      { path: 'agent/tools/create', name: 'ToolCreate', component: () => import('@/views/agent/tools/edit.vue'), meta: { title: '创建工具' } },
      { path: 'agent/tools/edit/:id', name: 'ToolEdit', component: () => import('@/views/agent/tools/edit.vue'), meta: { title: '编辑工具' } },
      { path: 'agent/tool-tags', name: 'ToolTags', component: () => import('@/views/agent/tool_tags/index.vue'), meta: { title: '工具标签' } },
      { path: 'agent/workflows', name: 'AgentWorkflows', component: () => import('@/views/agent/workflows/index.vue'), meta: { title: '工作流' } },
      { path: 'agent/workflows/edit/:id', name: 'WorkflowEdit', component: () => import('@/views/agent/workflows/edit.vue'), meta: { title: '编辑工作流' } },
      { path: 'agent/workflows/graph/:id', name: 'WorkflowGraph', component: () => import('@/views/agent/workflows/LangGraphEdit.vue'), meta: { title: '工作流结构图' } },
      { path: 'agent/executions', name: 'Executions', component: () => import('@/views/agent/executions.vue'), meta: { title: '执行记录' } },
      { path: 'agent/memory', name: 'AgentMemory', component: () => import('@/views/agent/memory/index.vue'), meta: { title: '记忆管理' } },
      { path: 'agent/dialog-flows', name: 'DialogFlows', component: () => import('@/views/agent/dialog-flows/index.vue'), meta: { title: '对话流' } },
      { path: 'agent/dialog-flows/edit/:id', name: 'DialogFlowEdit', component: () => import('@/views/agent/dialog-flows/edit.vue'), meta: { title: '编辑对话流' } },
      { path: 'agent/rag', name: 'RAG', component: () => import('@/views/agent/rag/index.vue'), meta: { title: 'RAG知识库' } },
      { path: 'joke/agent-debug', name: 'JokeAgentDebug', component: () => import('@/views/joke/agent-debug.vue'), meta: { title: '笑话智能体调试' } },
      // 财务管理模块
      {
        path: 'finance',
        name: 'Finance',
        component: () => import('@/views/finance/Index.vue'),
        redirect: 'finance/account',
        meta: { title: '财务管理', icon: 'Wallet' }
      },
      {
        path: 'finance/account',
        name: 'FinanceAccount',
        component: () => import('@/views/finance/account/Index.vue'),
        meta: { title: '会计科目' }
      },
      {
        path: 'finance/journal',
        name: 'FinanceJournal',
        component: () => import('@/views/finance/journal/Index.vue'),
        meta: { title: '凭证管理' }
      },
      {
        path: 'finance/report',
        name: 'FinanceReport',
        component: () => import('@/views/finance/report/Index.vue'),
        meta: { title: '财务报表' }
      },

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
  
  console.log('[路由守卫] 目标路径:', to.path, '当前路由列表:', router.getRoutes().map(r => r.path))

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
        console.log('[路由守卫] 生成的动态路由:', dynamicRoutes)
        dynamicRoutes.forEach(route => {
          // 直接添加到 panel 路由下
          router.addRoute('panel', route)
        })
        console.log('[路由守卫] 添加路由后路由列表:', router.getRoutes().map(r => r.path))
        
        // 重新进行路由匹配
        next({ ...to, replace: true })
        return
      } catch (error) {
        console.error('加载菜单失败:', error)
      }
    } else if (menuStore.isLoaded) {
      const resolved = router.resolve(to)
      if (resolved.matched.length === 0) {
        const dynamicRoutes = menuStore.generateRoutes()
        dynamicRoutes.forEach(route => {
          router.addRoute('panel', route)
        })
        next({ ...to, replace: true })
      } else {
        next()
      }
    } else if (menuStore.loading) {
      next(false)
    }
  }
})

export default router
