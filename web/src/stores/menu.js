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
  'Box': 'Box'
}

// 视图组件映射 - 根据后端返回的 component 路径映射到实际组件
const viewModules = import.meta.glob('@/views/**/*.vue')

// 根据 component 路径获取组件
function loadComponent(component) {
  if (!component) return null

  // 处理 component 路径
  let path = component
  if (!path.startsWith('/')) {
    path = '/' + path
  }
  if (!path.endsWith('.vue')) {
    path = path + '.vue'
  }

  // 尝试匹配视图组件
  const matchPath = `/src/views${path}`
  for (const [key, value] of Object.entries(viewModules)) {
    if (key.includes(matchPath) || key.endsWith(path)) {
      return value
    }
  }

  return null
}

export const useMenuStore = defineStore('menu', {
  state: () => ({
    // 原始菜单数据（从后端获取）
    menus: [],
    // 是否已加载菜单
    isLoaded: false,
    // 加载中状态
    loading: false
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
        // 后端返回 code=0 表示成功 (RET.OK)
        if ((res.code === 0 || res.code === 200 || res.success) && res.data) {
          this.menus = res.data
          this.isLoaded = true
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

      const processMenu = (menu, parentPath = '') => {
        // 跳过按钮类型
        if (menu.menu_type === 'button') return null

        const fullPath = menu.path?.startsWith('/')
          ? menu.path
          : `${parentPath}/${menu.path || ''}`.replace(/\/+/g, '/')

        const route = {
          path: fullPath,
          name: menu.name,
          meta: {
            title: menu.name,
            icon: menu.icon,
            permission: menu.permission,
            cached: menu.is_cached
          }
        }

        // 如果有组件路径，加载组件
        if (menu.component) {
          const component = loadComponent(menu.component)
          if (component) {
            route.component = component
          }
        }

        // 处理子菜单
        if (menu.children && menu.children.length > 0) {
          route.children = menu.children
            .map(child => processMenu(child, fullPath))
            .filter(Boolean)
        }

        return route
      }

      this.menus.forEach(menu => {
        const route = processMenu(menu)
        if (route) {
          routes.push(route)
        }
      })

      return routes
    },

    // 重置菜单状态
    resetMenus() {
      this.menus = []
      this.isLoaded = false
      this.loading = false
    }
  }
})
