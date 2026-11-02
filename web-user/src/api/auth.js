import request from '@/utils/request'

/**
 * 客户认证 API（T7）
 * 溯源：base/plugins/customer/api/v1/auth.py，挂载 /v1/customer/auth/*；
 * 登录响应附带 link_hint（RK-14），由 stores/auth 消费驱动提示卡。
 *
 * @typedef {Object} Customer
 * @property {number} id
 * @property {string} username
 * @property {string} email
 * @property {string} [nickname]
 * @property {boolean} is_active
 *
 * @typedef {Object} LoginResult
 * @property {string} access_token
 * @property {string} token_type   - 固定 'bearer'
 * @property {number} expires_in   - 秒
 * @property {Customer} customer
 * @property {boolean} [link_hint] - 是否提示身份关联（系统不自动绑定，R-14）
 */

/**
 * 密码登录
 * @param {{email: string, password: string}} data
 * @returns {Promise<{data: LoginResult}>}
 */
export function loginByPassword(data) {
  return request.post('/v1/customer/auth/login', data)
}

/**
 * 验证码登录
 * @param {{email: string, code: string}} data
 * @returns {Promise<{data: LoginResult}>}
 */
export function loginByCode(data) {
  return request.post('/v1/customer/auth/login-code', data)
}

/**
 * 发送验证码（登录场景 type=login）
 * @param {{email: string, type?: string}} data
 */
export function sendCode(data) {
  return request.post('/v1/customer/auth/send-code', { type: 'login', ...data })
}

/** 获取当前客户信息 */
export function getCurrentCustomer() {
  return request.get('/v1/customer/auth/me')
}

/** 登出（JWT 无状态，服务端仅记录，前端负责清理） */
export function logout() {
  return request.post('/v1/customer/auth/logout')
}
