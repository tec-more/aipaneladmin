/**
 * 执行 API（T12）
 * 溯源：u_execution_router（/v1/agent/u/*）。
 * dry-run 用原生 fetch（需 ReadableStream + Bearer + POST，axios 不便流式）；
 * 其余走 axios request 封装（401/429 归一化）。
 */
import request from '@/utils/request'
import { consumeSseStream } from '@/utils/sseParser'

/**
 * 发起试跑并流式消费事件（SSE）
 * @param {number} workflowId
 * @param {Object} inputs 触发输入（按 start.inputs）
 * @param {{onFrame:(f:{event:string,data:Object})=>void, signal?:AbortSignal}} opts
 * @returns {Promise<{executionId:number|null}>} 流结束后解析出的 execution_id
 * @throws 401/403/422/429 等（message 已归一）
 */
export async function dryRunStream(workflowId, inputs = {}, { onFrame, signal } = {}) {
  const token = localStorage.getItem('u_token')
  let resp
  try {
    resp = await fetch(`/api/v1/agent/u/workflows/${workflowId}/executions/dry-run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ inputs }),
      signal
    })
  } catch (e) {
    if (e?.name === 'AbortError') throw e
    throw new Error('网络错误，无法发起试跑')
  }

  if (!resp.ok) {
    let msg = `请求失败 (${resp.status})`
    try {
      const body = await resp.json()
      msg = body?.msg || body?.message || body?.error?.message || msg
    } catch { /* 保留默认 */ }
    const err = new Error(msg)
    err.status = resp.status
    throw err
  }

  const executionId = Number(resp.headers.get('X-Execution-Id')) || null
  if (!resp.body) return { executionId }
  await consumeSseStream(resp.body.getReader(), onFrame)
  return { executionId }
}

/** 取消执行（幂等） */
export function cancelExecution(executionId) {
  return request.post(`/v1/agent/u/executions/${executionId}/cancel`)
}

/** HITL 恢复（approve/reject） */
export function resumeExecution(executionId, { approved, comment } = {}) {
  return request.post(`/v1/agent/u/executions/${executionId}/resume`, { approved, comment })
}

/** 执行详情 */
export function getExecution(executionId) {
  return request.get(`/v1/agent/u/executions/${executionId}`)
}

/**
 * 增量 trace 回放（断线补齐：cursor=lastSeq，返回 seq>cursor 事件）
 * @returns Promise<{items:TraceEvent[], next_cursor:number}>
 */
export function getExecutionTrace(executionId, cursor = 0, limit = 200) {
  return request.get(`/v1/agent/u/executions/${executionId}/trace`, { params: { cursor, limit } })
}
