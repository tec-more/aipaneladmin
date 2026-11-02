/**
 * 执行态 store（T12）
 * 职责：SSE 事件 → 运行态归约（seq 着色源）、trace 缓冲、断线补齐（trace?cursor）、控制（取消/HITL 恢复）。
 * 禁区：不直连画布组件（组件读 nodeState 渲染）；不臆断状态（只认事件序，后到 seq 覆盖）。
 * 状态机（节点2 §3）：idle/connecting/streaming/paused/replaying/completed/failed/cancelled
 */
import { defineStore } from 'pinia'
import { dryRunStream, cancelExecution, resumeExecution, getExecutionTrace } from '@/api/execution'

/** 终态事件（trace 补齐/轮询终止条件） */
const TERMINAL = new Set(['run_completed', 'run_failed', 'run_cancelled'])
/** 断线/恢复轮询间隔与上限 */
const POLL_INTERVAL = 800
const POLL_MAX = 75 // ≈60s

export const useExecutionStore = defineStore('execution', {
  state: () => ({
    status: 'idle',
    executionId: null,
    workflowId: null,
    /** 节点运行态：node_id -> {status,seq,ms,usage,error}（画布着色唯一数据源） */
    nodeState: {},
    /** 全量 trace 事件（Trace 面板数据源，按 seq 升序） */
    events: [],
    /** 断点（断线补齐 cursor） */
    lastSeq: 0,
    /** token 流式聚合：node_id -> 文本（R-A：仅 Trace 用，不刷节点） */
    tokenBuffer: {},
    /** HITL 挂起态：{node_id, assignee, deadline} */
    hitl: null,
    /** 运行结果：{tokens, ms, error} */
    runMeta: null,
    /** 断线/中断提示 */
    notice: ''
  }),

  getters: {
    running: (s) => ['connecting', 'streaming', 'paused', 'replaying'].includes(s.status),
    isTerminal: (s) => ['completed', 'failed', 'cancelled'].includes(s.status),
    /** 画布着色用：节点状态映射（响应式） */
    nodeStatusMap: (s) => s.nodeState,
    totalTokens: (s) => s.runMeta?.tokens ?? null
  },

  actions: {
    /** 重置（新试跑/离开编辑器） */
    reset() {
      this._abort()
      this.status = 'idle'
      this.executionId = null
      this.workflowId = null
      this.nodeState = {}
      this.events = []
      this.lastSeq = 0
      this.tokenBuffer = {}
      this.hitl = null
      this.runMeta = null
      this.notice = ''
    },

    /**
     * 发起试跑：SSE 流式归约；断线自动 trace 补齐（Q2 裁定）
     * @param {number} workflowId @param {Object} inputs
     */
    async start(workflowId, inputs = {}) {
      if (this.running) return
      this.reset()
      this.workflowId = workflowId
      this.status = 'connecting'
      this._aborter = new AbortController()
      try {
        const { executionId } = await dryRunStream(workflowId, inputs, {
          signal: this._aborter.signal,
          onFrame: (f) => this._applyFrame(f)
        })
        if (executionId && !this.executionId) this.executionId = executionId
        // 流正常结束但未达终态（如 paused 后服务端保持）→ 不强制补齐，等用户操作
      } catch (e) {
        if (e?.name === 'AbortError') return // 用户取消/离开
        // 断线：转 replay 补齐（Q2）
        this.notice = '连接中断，已切换回放补齐'
        await this._replayUntilTerminal()
      }
    },

    /** 取消（仅运行中可调；幂等） */
    async cancel() {
      if (!this.executionId || !this.running) return
      try {
        await cancelExecution(this.executionId)
        this._abort()
        this.status = 'cancelled'
      } catch { /* 拦截器已提示 */ }
    },

    /** HITL 恢复（approve/reject）；resume 后 SSE 已终，转轮询 trace 补齐至终态 */
    async resume(approved, comment) {
      if (!this.executionId) return
      try {
        await resumeExecution(this.executionId, { approved, comment })
        this.hitl = null
        this.status = 'streaming'
        await this._replayUntilTerminal()
      } catch { /* 拦截器已提示 */ }
    },

    // ===== 内部：事件归约 =====
    /** SSE 帧 → 状态归约（只认事件序） */
    _applyFrame({ event, data }) {
      const seq = typeof data?.seq === 'number' ? data.seq : this.lastSeq
      if (seq > this.lastSeq) this.lastSeq = seq
      if (data?.execution_id && !this.executionId) this.executionId = data.execution_id
      this.events.push({ seq, event_type: event, node_id: data?.node_id, payload: data, created_at: new Date().toISOString() })

      const nid = data?.node_id
      switch (event) {
        case 'run_started':
          this.status = 'streaming'
          break
        case 'node_started':
          if (nid) this.nodeState[nid] = { status: 'running', seq }
          break
        case 'token':
          // R-A：聚合不刷节点
          if (nid) this.tokenBuffer[nid] = (this.tokenBuffer[nid] || '') + (data?.delta || '')
          break
        case 'node_completed':
          if (nid) this.nodeState[nid] = { status: 'completed', seq, ms: data?.ms, usage: data?.usage }
          break
        case 'node_failed':
          if (nid) this.nodeState[nid] = { status: 'failed', seq, error: data?.error }
          break
        case 'run_paused':
          this.status = 'paused'
          this.hitl = { node_id: nid, assignee: data?.assignee, deadline: data?.deadline }
          if (nid) this.nodeState[nid] = { status: 'paused', seq }
          break
        case 'run_completed':
          this.status = 'completed'
          this.runMeta = { tokens: data?.usage?.tokens ?? data?.tokens, ms: data?.ms }
          break
        case 'run_failed':
          this.status = 'failed'
          this.runMeta = { error: data?.error }
          break
        default:
          break
      }
    },

    /** trace 事件 → 复用归约（与 SSE 同构，event_type 即事件名） */
    _applyTrace(ev) {
      this._applyFrame({ event: ev.event_type, data: { ...(ev.payload || {}), seq: ev.seq, node_id: ev.node_id, execution_id: this.executionId } })
    },

    /** 断线/恢复补齐：cursor 分页轮询至终态（Q2）；页用尽且无推进即停 */
    async _replayUntilTerminal() {
      if (!this.executionId) { this.status = 'failed'; return }
      this.status = 'replaying'
      let idle = 0
      for (let i = 0; i < POLL_MAX; i++) {
        if (TERMINAL.has(this._lastEventType())) break
        try {
          const res = await getExecutionTrace(this.executionId, this.lastSeq, 200)
          const items = res?.data?.items || res?.items || []
          const nextCursor = res?.data?.next_cursor ?? res?.next_cursor ?? this.lastSeq
          if (items.length) {
            items.forEach((ev) => this._applyTrace(ev))
            idle = 0
          } else {
            idle++
          }
          this.lastSeq = Math.max(this.lastSeq, nextCursor)
          if (TERMINAL.has(this._lastEventType())) break
          if (idle >= 3) break // 无新事件且非终态：可能 paused，交还控制权
        } catch {
          idle++
          if (idle >= 3) break
        }
        await new Promise((r) => setTimeout(r, POLL_INTERVAL))
      }
      // 收尾：未达终态则保持 replaying/paused 现状（由后续 SSE/操作推进）
      if (!TERMINAL.has(this._lastEventType()) && this.status === 'replaying') {
        this.status = this.hitl ? 'paused' : 'streaming'
      }
    },

    _lastEventType() {
      return this.events.length ? this.events[this.events.length - 1].event_type : ''
    },

    _abort() {
      if (this._aborter) { try { this._aborter.abort() } catch { /* 忽略 */ } this._aborter = null }
    }
  }
})
