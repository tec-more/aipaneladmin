import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

/**
 * 用户侧 axios 封装（T7）
 * 溯源：docs/arch/04 §2 统一响应 {code, message, data}；
 * 与后台 web/ 工程通过 localStorage 键 `u_token`/`u_customer` 隔离（A2 独立站点）。
 * R-12：拦截器不打印请求体与凭证，错误提示仅透传 msg。
 */

const request = axios.create({
  baseURL: '/api',
  timeout: 15000
})

// 请求拦截：注入客户 token（typ=cus，由后端 M8 判定归属，前端不解析）
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('u_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截：统一包络拆解 + 鉴权/配额错误归一化
request.interceptors.response.use(
  (response) => {
    // 文件下载等原始响应直接放行
    if (response.config.responseType === 'blob') {
      return response
    }
    const res = response.data
    if (res.code === 0 || res.code === 200 || res.success === true || (res.items !== undefined)) {
      return res
    }
    ElMessage.error(res.msg || res.message || '请求失败')
    return Promise.reject(new Error(res.msg || res.message || '请求失败'))
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        // 登录失效：清理客户会话并回登录页（带回跳）
        localStorage.removeItem('u_token')
        localStorage.removeItem('u_customer')
        ElMessage.error('登录已过期，请重新登录')
        const redirect = router.currentRoute.value.fullPath
        router.push({ path: '/login', query: redirect && redirect !== '/login' ? { redirect } : {} })
      } else if (status === 403) {
        ElMessage.error(data?.msg || data?.message || '没有权限访问')
      } else if (status === 429) {
        // 配额/限流（429xx 段位）：透传后端提示（含剩余额度说明）
        ElMessage.error(data?.msg || data?.message || '额度不足或请求过于频繁')
      } else {
        ElMessage.error(data?.msg || data?.message || error.message || `请求失败 (${status})`)
      }
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error(error.message || '请求失败')
    }
    return Promise.reject(error)
  }
)

export default request
