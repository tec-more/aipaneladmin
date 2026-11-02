import request from '@/utils/request'

/**
 * 身份关联 API（T14 补全）
 * 溯源：base/plugins/customer/api/v1/identity.py，挂载 /v1/customer/identity/*；
 * PRD §3.3：提示→主动确认→验证，前端不发起任何自动绑定（R-14）。
 *
 * 错误数据透传约定：
 * 后端 fail_response(msg, data) 走 HTTP 400 + axios error 分支，
 * 拦截器 toast 后 reject 原始 error。本模块在 catch 中提取
 * err.response.data.data 挂到 err.bizData，便于视图读取 attempts_left /
 * lock_remaining_seconds / cooldown_until 等业务字段驱动 UI。
 *
 * @typedef {Object} PeerPrincipal
 * @property {'cus'|'usr'} owner_type
 * @property {string} username
 * @property {string} masked_email
 * @property {string|null} last_login
 *
 * @typedef {Object} LinkStatus
 * @property {'none'|'prompted'|'linked'|'dismissed'|'cooldown'} status
 * @property {boolean} should_prompt
 * @property {PeerPrincipal|null} peer
 * @property {string} [linked_at]
 * @property {string} [verified_via]
 * @property {string} [dismissed_until]
 * @property {string} [reason]
 * @property {string} [message]
 */

/** 提取后端 fail_response 中的 data 段，挂到 err.bizData */
function withBizData(promise) {
  return promise.catch((err) => {
    const bizData = err?.response?.data?.data
    if (bizData && typeof bizData === 'object') {
      err.bizData = bizData
    }
    throw err
  })
}

/** 查询关联提示状态 @returns {Promise<{data: LinkStatus}>} */
export function getLinkStatus() {
  return request.get('/v1/customer/identity/link-status')
}

/**
 * 发起身份关联（需验证）
 * @param {{verify_via: 'password'|'email_code', credential: string}} data
 * @returns {Promise<{data: {status, linked_at, peer, notice}}>}
 */
export function linkIdentity(data) {
  return withBizData(request.post('/v1/customer/identity/link', data))
}

/**
 * 解除关联（需验证，冷却 30 天）
 * @param {{verify_via: 'password'|'email_code', credential: string}} data
 * @returns {Promise<{data: {status, cooldown_until}}>}
 */
export function unlinkIdentity(data) {
  return withBizData(request.post('/v1/customer/identity/unlink', data))
}

/**
 * 不再提示（30 天）
 * @returns {Promise<{data: {status, dismissed_until}}>}
 */
export function dismissIdentity() {
  return withBizData(request.post('/v1/customer/identity/dismiss'))
}

/**
 * 发送身份关联验证码（60s 限频，SMTP 故障返回明确错误）
 * @returns {Promise<{msg}>}
 */
export function sendLinkCode() {
  return withBizData(request.post('/v1/customer/identity/send-code'))
}

/**
 * 重新开启提示（T14+ K2）
 * 仅 dismissed 状态可恢复；cooldown 期间拒绝（err.bizData.cooldown_until）
 * @returns {Promise<{data: {status:'prompted'}}>}
 */
export function resumeIdentity() {
  return withBizData(request.post('/v1/customer/identity/resume'))
}

/**
 * @typedef {Object} IdentityAuditEvent
 * @property {string} action    - prompt_shown/link_initiated/verify_failed/linked/dismissed/unlinked/resumed/admin_bind
 * @property {string} actor     - "cus:12" / "usr:5"
 * @property {string} at        - ISO 时间
 * @property {string|null} trace_id
 * @property {Object} detail
 */

/**
 * 身份操作历史（T14+ K4，L10 用户可查）
 * @returns {Promise<{data: {items: IdentityAuditEvent[], total: number}}>}
 */
export function getIdentityAudit() {
  return request.get('/v1/customer/identity/audit')
}
