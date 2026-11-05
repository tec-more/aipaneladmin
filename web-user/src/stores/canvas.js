/**
 * 画布状态 store（T8）
 * 职责：图数据源（VueFlow v-model 绑定）、撤销/重做历史栈、校验态、保存态。
 * 禁区：不直接发请求（经 api 层）；不内置校验规则（调 @validator）；不执行节点逻辑（M1 红线）。
 * 撤销/重做：快照式（T8 节点1 裁定 Q3），上限 50 步，覆盖节点增删/连线/移动/改名。
 */
import { defineStore } from 'pinia'
import { validateGraph } from '@validator'
import { toVueFlow, toGraph } from '@/utils/graphSerializer'

const HISTORY_LIMIT = 50

/** 深拷贝快照（纯 JSON 图数据） */
function deepSnap(nodes, edges, meta, variables, settings) {
  return JSON.parse(JSON.stringify({ nodes, edges, meta, variables, settings }))
}

export const useCanvasStore = defineStore('canvas', {
  state: () => ({
    workflowId: null,
    // VueFlow 数据源（v-model:nodes / v-model:edges）
    nodes: [],
    edges: [],
    meta: { name: '', description: '', icon: '' },
    variables: [],
    settings: null,
    // 乐观锁版本（服务端权威）
    draftVersion: 0,
    // 选中态
    selectedNodeId: null,
    selectedEdgeId: null,
    // 校验态：local=本地预检；server=服务端返回（含 E-108/E-110）
    localIssues: [],
    serverIssues: [],
    serverSummary: null,
    // 保存态
    saving: false,
    dirty: false,
    lastSavedAt: null,
    // 历史栈
    past: [],
    future: []
  }),

  getters: {
    /** 问题面板双源合并（服务端 issue 结构与本包同构，零转换） */
    allIssues(state) {
      return [...state.localIssues, ...state.serverIssues]
    },
    /** 按节点分组的错误级 issue（画布角标） */
    errorNodeIds(state) {
      const set = new Set()
      for (const it of state.localIssues.concat(state.serverIssues)) {
        if (it.level === 'error' && it.node_id) set.add(it.node_id)
      }
      return set
    },
    canUndo: (state) => state.past.length > 0,
    canRedo: (state) => state.future.length > 0,
    /** 是否存在阻断级问题（发布前置，T13 消费） */
    hasBlockingIssues(state) {
      return state.localIssues.concat(state.serverIssues).some((i) => i.level === 'error')
    }
  },

  actions: {
    /** 装载详情（打开编辑器） */
    loadDetail(detail) {
      const def = detail?.definition || {}
      const { nodes, edges } = toVueFlow(def)
      this.workflowId = detail?.id ?? null
      this.nodes = nodes
      this.edges = edges
      this.meta = {
        name: detail?.name || def?.meta?.name || '未命名工作流',
        description: detail?.description || def?.meta?.description || '',
        icon: detail?.icon || def?.meta?.icon || ''
      }
      this.variables = Array.isArray(def?.variables) ? def.variables : []
      this.settings = def?.settings || null
      this.draftVersion = detail?.draft_version ?? 0
      this.localIssues = []
      this.serverIssues = Array.isArray(detail?.validation?.issues) ? detail.validation.issues : []
      this.serverSummary = detail?.validation || null
      this.dirty = false
      this.selectedNodeId = null
      this.selectedEdgeId = null
      this.past = []
      this.future = []
    },

    /** 重置（离开编辑器） */
    reset() {
      this.workflowId = null
      this.nodes = []
      this.edges = []
      this.meta = { name: '', description: '', icon: '' }
      this.variables = []
      this.settings = null
      this.draftVersion = 0
      this.selectedNodeId = null
      this.selectedEdgeId = null
      this.localIssues = []
      this.serverIssues = []
      this.serverSummary = null
      this.saving = false
      this.dirty = false
      this.lastSavedAt = null
      this.past = []
      this.future = []
    },

    /** 入栈快照（任何变更前调用）；label 仅调试用途 */
    snapshot() {
      this.past.push(deepSnap(this.nodes, this.edges, this.meta, this.variables, this.settings))
      if (this.past.length > HISTORY_LIMIT) this.past.shift()
      this.future = []
    },

    _restore(snap) {
      this.nodes = snap.nodes
      this.edges = snap.edges
      this.meta = snap.meta
      this.variables = snap.variables
      this.settings = snap.settings
      this.dirty = true
      this.selectedNodeId = null
      this.selectedEdgeId = null
      this.runLocalValidate()
    },

    undo() {
      if (!this.past.length) return false
      this.future.push(deepSnap(this.nodes, this.edges, this.meta, this.variables, this.settings))
      this._restore(this.past.pop())
      return true
    },

    redo() {
      if (!this.future.length) return false
      this.past.push(deepSnap(this.nodes, this.edges, this.meta, this.variables, this.settings))
      this._restore(this.future.pop())
      return true
    },

    // ===== 图变更（统一经 snapshot → 变更 → dirty → 本地校验）=====
    addNode(vueNode) {
      this.snapshot()
      this.nodes.push(vueNode)
      this._afterChange()
    },

    removeNode(nodeId) {
      this.snapshot()
      this.edges = this.edges.filter((e) => e.source !== nodeId && e.target !== nodeId)
      this.nodes = this.nodes.filter((n) => n.id !== nodeId)
      if (this.selectedNodeId === nodeId) this.selectedNodeId = null
      this._afterChange()
    },

    removeEdge(edgeId) {
      this.snapshot()
      this.edges = this.edges.filter((e) => e.id !== edgeId)
      if (this.selectedEdgeId === edgeId) this.selectedEdgeId = null
      this._afterChange()
    },

    /** 连线落图（调用方须先过 validateConnection） */
    applyConnect(conn, edgeId) {
      this.snapshot()
      this.edges.push({
        id: edgeId,
        source: conn.source,
        sourceHandle: conn.sourceHandle,
        target: conn.target,
        targetHandle: conn.targetHandle,
        type: 'smoothstep'
      })
      this._afterChange()
    },

    /** 拖拽结束后的位置提交（拖拽过程不入历史，dragStop 一次性入栈） */
    commitMove() {
      this.snapshot()
      // 交换顺序：snapshot 存的是移动前状态；位置已在 nodes 上，直接标记
      this._afterChange()
    },

    /** 更新节点显示名/描述（配置壳用） */
    updateNodeMeta(nodeId, patch) {
      const node = this.nodes.find((n) => n.id === nodeId)
      if (!node) return
      this.snapshot()
      node.data.label = patch.label ?? node.data.label
      this._afterChange()
    },

    /** 更新节点 config（T10 表单写入通道；T8 仅壳占位） */
    updateNodeConfig(nodeId, config) {
      const node = this.nodes.find((n) => n.id === nodeId)
      if (!node) return
      this.snapshot()
      node.data.config = config
      this._afterChange()
    },

    selectNode(nodeId) {
      this.selectedNodeId = nodeId
      this.selectedEdgeId = null
    },

    selectEdge(edgeId) {
      this.selectedEdgeId = edgeId
      this.selectedNodeId = null
    },

    clearSelection() {
      this.selectedNodeId = null
      this.selectedEdgeId = null
    },

    _afterChange() {
      this.dirty = true
      this.runLocalValidate()
    },

    /** 本地全量校验（E-100~E-112，除 server-only 项） */
    runLocalValidate() {
      const graph = this.collectGraph()
      this.localIssues = validateGraph(graph)
      return this.localIssues
    },

    /** 组装 Schema v2（保存/服务端校验用） */
    collectGraph() {
      return toGraph(this.nodes, this.edges, this.meta, this.variables, this.settings)
    },

    /** 保存成功回写 */
    markSaved({ draft_version, updated_at, validation }) {
      if (typeof draft_version === 'number') this.draftVersion = draft_version
      this.dirty = false
      this.lastSavedAt = updated_at || new Date().toISOString()
      this.serverIssues = Array.isArray(validation?.issues) ? validation.issues : []
      this.serverSummary = validation || null
    }
  }
})
