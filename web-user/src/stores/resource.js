import { defineStore } from 'pinia'
import { getMyResources } from '@/api/resource'

/**
 * 资源授权缓存 store（T11）
 * 会话级缓存（R-A）：避免每次打开选择器/进编辑器都请求；授权可变性由
 * 保存期 E-110（服务端权威）兜底，故不持久化 localStorage。
 */
export const useResourceStore = defineStore('resource', {
  state: () => ({
    /** @type {Object<string, Array>} type -> items 缓存 */
    cache: {},
    /** @type {Object<string, boolean>} type -> 是否已加载（区分"空授权"与"未加载"） */
    loaded: {},
    loading: false
  }),

  getters: {
    /** node_type 授权集：画布节点库动态置灰数据源 */
    grantedNodeTypes: (state) => new Set((state.cache.node_type || []).map((i) => i.id)),
    /** 指定类型授权资源清单 */
    itemsOf: (state) => (type) => state.cache[type] || [],
    isLoaded: (state) => (type) => !!state.loaded[type]
  },

  actions: {
    /** 加载某类资源（幂等：已加载则直接返回；force 强制刷新） */
    async load(type, force = false) {
      if (this.loaded[type] && !force) return this.cache[type]
      this.loading = true
      try {
        const res = await getMyResources(type)
        this.cache[type] = res.data?.items || []
        this.loaded[type] = true
        return this.cache[type]
      } finally {
        this.loading = false
      }
    },

    /** 失效缓存（授权变更后调用；当前仅登出时清空） */
    invalidate(type) {
      if (type) { delete this.cache[type]; delete this.loaded[type] }
      else { this.cache = {}; this.loaded = {} }
    }
  }
})
