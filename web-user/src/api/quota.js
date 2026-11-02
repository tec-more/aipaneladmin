import request from '@/utils/request'

/**
 * 配额看板 API（T14）
 * 溯源：base/plugins/customer/api/v1/quota_router.py，挂载 /v1/customer/quota；
 * 实现：base/common/quota/services/quota_service.py QuotaService.board()。
 *
 * @typedef {Object} QuotaItem
 * @property {string} item   - 配额项编码：token/concurrency/daily_runs/kb_search/vector_write/...
 * @property {number} limit  - 周期上限
 * @property {number} used   - 已用量（concurrency 项为当前并发数）
 * @property {number} held   - 预占量（concurrency 项通常为 0）
 *
 * @typedef {Object} QuotaBoard
 * @property {string|null} plan         - 套餐编码（未绑套餐为 null）
 * @property {string|null} plan_name    - 套餐名称
 * @property {string} period            - 周期标识 YYYY-MM
 * @property {string|null} period_start - ISO 时间
 * @property {string|null} period_end   - ISO 时间
 * @property {QuotaItem[]} items
 */

/**
 * 当前主体配额看板
 * @returns {Promise<{data: QuotaBoard}>}
 */
export function getQuotaBoard() {
  return request.get('/v1/customer/quota')
}

/**
 * @typedef {Object} UsageRecordItem
 * @property {number} id
 * @property {number|null} execution_id
 * @property {string|null} node_id
 * @property {string} resource_type
 * @property {number} amount
 * @property {number} tokens_in
 * @property {number} tokens_out
 * @property {number} cost
 * @property {string} created_at
 *
 * @typedef {Object} UsageRecordPage
 * @property {number} total
 * @property {number} page
 * @property {number} page_size
 * @property {UsageRecordItem[]} items
 */

/**
 * 当前主体用量流水（T14+ K3，归属过滤由服务端强制）
 * @param {{execution_id?:number, resource_type?:string, start_time?:string, end_time?:string, page?:number, page_size?:number}} params
 * @returns {Promise<{data: UsageRecordPage}>}
 */
export function getUsageRecords(params) {
  return request.get('/v1/customer/usage-records', { params })
}
