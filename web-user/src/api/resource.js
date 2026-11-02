/**
 * 用户侧资源授权清单 API（T11）
 * 路径溯源：/v1/agent/u/resources（T11 节点2 §3 契约）
 * 仅返回已授权资源；授权判定权威在服务端保存期 E-110。
 */
import request from '@/utils/request'

/**
 * 当前主体已授权资源清单
 * @param {'model'|'kb'|'tool'|'agent'|'node_type'} type
 * @returns {Promise<{items: Array<{id:string,label:string,extra:Object,expires_at:string|null}>}>}
 */
export function getMyResources(type) {
  return request({ url: '/v1/agent/u/resources', method: 'get', params: { type } })
}
