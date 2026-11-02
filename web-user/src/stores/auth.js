import { defineStore } from 'pinia'
import { loginByPassword, loginByCode, getCurrentCustomer, logout as logoutApi } from '@/api/auth'

/**
 * 客户会话 store（T7）
 * 存储键 `u_token`/`u_customer` 与后台 `token`/`userInfo` 隔离（A2 独立站点）；
 * link_hint 仅存内存 + 会话级关闭标记（sessionStorage），刷新后由登录响应重新驱动。
 */
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('u_token') || '',
    customer: JSON.parse(localStorage.getItem('u_customer') || '{}'),
    /** @type {boolean} 登录响应下发的身份关联提示（RK-14） */
    linkHint: false,
    /** 会话级"暂不关联"标记（L4：仅本次会话不再出现） */
    linkHintDismissed: sessionStorage.getItem('u_link_hint_dismissed') === '1'
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    nickname: (state) => state.customer?.nickname || state.customer?.username || '',
    email: (state) => state.customer?.email || '',
    /** 是否应展示身份关联提示卡 */
    shouldShowLinkHint: (state) => state.linkHint && !state.linkHintDismissed
  },

  actions: {
    /** 统一登录入口：mode = 'password' | 'code' */
    async login(mode, payload) {
      const api = mode === 'code' ? loginByCode : loginByPassword
      const res = await api(payload)
      const { access_token, customer, link_hint } = res.data

      this.token = access_token
      this.customer = customer
      this.linkHint = !!link_hint
      this.linkHintDismissed = false

      localStorage.setItem('u_token', access_token)
      localStorage.setItem('u_customer', JSON.stringify(customer))
      sessionStorage.removeItem('u_link_hint_dismissed')
      return res
    },

    /** 刷新当前客户信息（容错：失败不阻断，保留本地快照） */
    async fetchCustomer() {
      try {
        const res = await getCurrentCustomer()
        this.customer = res.data
        localStorage.setItem('u_customer', JSON.stringify(res.data))
      } catch (e) {
        // 401 已由拦截器统一处理回登录页；其余失败保留本地快照
      }
      return this.customer
    },

    /** 暂不关联：仅本次会话生效（L4） */
    dismissLinkHint() {
      this.linkHintDismissed = true
      sessionStorage.setItem('u_link_hint_dismissed', '1')
    },

    async logout() {
      try {
        await logoutApi()
      } catch (e) {
        // 登出接口失败不阻断本地清理
      }
      this.token = ''
      this.customer = {}
      this.linkHint = false
      this.linkHintDismissed = false
      localStorage.removeItem('u_token')
      localStorage.removeItem('u_customer')
      sessionStorage.removeItem('u_link_hint_dismissed')
    }
  }
})
