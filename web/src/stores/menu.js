import { defineStore } from 'pinia'
import { getUserMenus } from '@/api/rbac'

// 图标映射表
const iconMap = {
  'Odometer': 'Odometer',
  'Setting': 'Setting',
  'User': 'User',
  'OfficeBuilding': 'OfficeBuilding',
  'UserFilled': 'UserFilled',
  'Key': 'Key',
  'Menu': 'Menu',
  'Connection': 'Connection',
  'Document': 'Document',
  'Folder': 'Folder',
  'Files': 'Files',
  'Grid': 'Grid',
  'List': 'List',
  'Search': 'Search',
  'Edit': 'Edit',
  'Delete': 'Delete',
  'Plus': 'Plus',
  'Minus': 'Minus',
  'Check': 'Check',
  'Close': 'Close',
  'Warning': 'Warning',
  'Info': 'InfoFilled',
  'Question': 'QuestionFilled',
  'Star': 'Star',
  'Message': 'Message',
  'Bell': 'Bell',
  'Calendar': 'Calendar',
  'Clock': 'Clock',
  'Location': 'Location',
  'Phone': 'Phone',
  'Picture': 'Picture',
  'Video': 'VideoCamera',
  'Upload': 'Upload',
  'Download': 'Download',
  'Link': 'Link',
  'Share': 'Share',
  'Lock': 'Lock',
  'Unlock': 'Unlock',
  'Tools': 'Tools',
  'Monitor': 'Monitor',
  'DataLine': 'DataLine',
  'PieChart': 'PieChart',
  'TrendCharts': 'TrendCharts',
  'Histogram': 'Histogram',
  'ShoppingCart': 'ShoppingCart',
  'Money': 'Money',
  'Box': 'Box',
  'ShieldCheck': 'ShieldCheck',
  'FileCheck': 'FileCheck',
  'BookOpen': 'BookOpen',
  'Settings': 'Settings',
  'Wrench': 'Wrench',
  'AlertTriangle': 'AlertTriangle',
  'Wallet': 'Wallet',
  'FileText': 'FileText',
  'Columns': 'Columns',
  'TrendingUp': 'TrendingUp',
  'BarChart3': 'BarChart3',
  'Activity': 'Activity',
  'CloudServer': 'CloudServer',
  'Bot': 'Bot',
  'Management': 'Management',
  'DataAnalysis': 'DataAnalysis',
  'UserFilled': 'UserFilled',
  'BookMark': 'BookMark',
  'CreditCard': 'CreditCard',
  'TrendingDown': 'TrendingDown',
  'Banknote': 'Banknote',
  'CheckCircle': 'CheckCircle',
  'Building2': 'Building2',
  'Calculator': 'Calculator',
  'RefreshCw': 'RefreshCw',
  'Trash2': 'Trash2',
  'Package': 'Package',
  'FileSpreadsheet': 'FileSpreadsheet',
  'ArrowRightLeft': 'ArrowRightLeft',
  'Bank': 'Bank',
  'Landmark': 'Landmark',
  'CalendarCheck': 'CalendarCheck',
  'Table': 'Table',
  'Layout': 'Layout',
  'Receipt': 'Receipt',
  'FileEdit': 'FileEdit',
  'CheckSquare': 'CheckSquare',
  'Send': 'Send',
  'Inbox': 'Inbox'
}

// 视图组件映射 - 根据后端返回的 component 路径映射到实际组件
const viewModules = import.meta.glob('@/views/**/*.vue', { eager: false })

// 根据 component 路径获取组件
function loadComponent(component) {
  if (!component) return null

  const normalizedComponent = component.replace(/^\//, '')

  const possiblePatterns = [
    `${normalizedComponent}.vue`,
    `${normalizedComponent}/index.vue`,
    normalizedComponent,
    `${normalizedComponent}/index`
  ]

  for (const pattern of possiblePatterns) {
    const searchKey = `@/views/${pattern}`
    if (viewModules[searchKey]) {
      return viewModules[searchKey]
    }

    for (const [key, value] of Object.entries(viewModules)) {
      if (key.endsWith(`/${pattern}`) || key === searchKey) {
        return value
      }
    }
  }

  console.warn(`[菜单Store] 找不到组件: ${component}，返回 NotFound`)
  return () => import('@/views/NotFound.vue')
}

export const useMenuStore = defineStore('menu', {
  state: () => ({
    // 原始菜单数据（从后端获取）
    menus: [],
    // 是否已加载菜单
    isLoaded: false,
    // 加载中状态
    loading: false,
    // 动态路由是否已注入
    routesReady: false,
    // 动态路由名称列表（用于追踪已添加的路由）
    dynamicRouteNames: [],
    // 路由重试计数器（防止无限重定向循环）
    routeRetryCount: 0
  }),

  getters: {
    // 获取菜单树
    menuTree: (state) => state.menus,

    // 获取图标名称
    getIconName: () => (iconName) => {
      return iconMap[iconName] || iconName || 'Document'
    }
  },

  actions: {
    // 从后端加载用户菜单
    async fetchUserMenus() {
      if (this.loading) return

      this.loading = true
      try {
        const res = await getUserMenus()
        console.log('[菜单Store] 获取到的菜单数据:', res)
        // 后端返回 code=0 表示成功 (RET.OK)
        if ((res.code === 0 || res.code === 200 || res.success) && res.data) {
          this.menus = res.data
          this.isLoaded = true
          console.log('[菜单Store] 菜单数据已保存:', this.menus)
        }
      } catch (error) {
        console.error('加载菜单失败:', error)
        this.menus = []
      } finally {
        this.loading = false
      }
    },

    // 生成动态路由
    generateRoutes() {
      const routes = []
      console.log('[菜单Store] generateRoutes 开始处理菜单:', this.menus)

      const flattenMenu = (menu) => {
        console.log('[菜单Store] 处理菜单:', menu)
        if (menu.menu_type === 'button') return []

        const result = []

        let routePath = menu.path || ''
        
        if (routePath.startsWith('/panel')) {
          routePath = routePath.replace(/^\/panel/, '')
        }
        if (routePath.startsWith('/')) {
          routePath = routePath.substring(1)
        }
        
        routePath = routePath.replace(/\/+/g, '/').replace(/\/$/, '')
        
        console.log('[菜单Store] 菜单路径:', menu.path, '转换后:', routePath)

        if (menu.component) {
          const route = {
            path: routePath,
            name: menu.name,
            meta: {
              title: menu.name,
              icon: menu.icon,
              permission: menu.permission,
              cached: menu.is_cached
            }
          }

          const component = loadComponent(menu.component)
          console.log('[菜单Store] 加载组件:', menu.component, '结果:', component)
          if (component) {
            route.component = component
          } else {
            route.component = () => import('@/views/NotFound.vue')
          }

          result.push(route)
        }

        if (menu.children && menu.children.length > 0) {
          menu.children.forEach(child => {
            result.push(...flattenMenu(child))
          })
        }

        return result
      }

      this.menus.forEach(menu => {
        if (menu.menu_type !== 'button') {
          routes.push(...flattenMenu(menu))
        }
      })

      routes.sort((a, b) => {
        return b.path.split('/').length - a.path.split('/').length
      })

      console.log('[菜单Store] generateRoutes 完成，生成的路由:', routes)
      return routes
    },

    // 重置菜单状态
    resetMenus() {
      this.menus = []
      this.isLoaded = false
      this.loading = false
      this.routesReady = false
      this.dynamicRouteNames = []
      this.routeRetryCount = 0
    }
  }
})