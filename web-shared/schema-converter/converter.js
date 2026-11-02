/**
 * v1→v2 转换主逻辑（纯函数，零 I/O）
 * 流程：输入归一 → 逐节点转换 → 边转换（端口补齐/分支判定）→ 组装 Schema v2 →
 *       @validator 全量校验闭环 → issues（E-1xx + W-2xx）+ report。
 * 幂等：纯函数，同一输入必得同一产物（节点 id 沿用 v1，不生成随机量）。
 */
import { validateGraph, getNodeMeta } from '../schema-validator/index.js'
import {
  V1_NODE_MAPPING, DEFAULT_TARGET_HANDLE, DEFAULT_SOURCE_HANDLE, mapConditionBranch
} from './mapping.js'
import { makeWarn, createReport, addNodeDiff, addEdgeDiff } from './report.js'

/** 简易分层布局：v1 无 position 时重建（BFS 深度分列），记 W-204 */
function layoutPositions(nodes, edges) {
  const pos = new Map()
  const hasAnyPos = nodes.some((n) => n.position && typeof n.position.x === 'number')
  if (hasAnyPos) {
    nodes.forEach((n) => pos.set(n.id, n.position || { x: 0, y: 0 }))
    return { pos, rebuilt: false }
  }
  const start = nodes.find((n) => n.type === 'start') || nodes[0]
  const depth = new Map()
  const adj = new Map()
  for (const e of edges) {
    if (!adj.has(e.source)) adj.set(e.source, [])
    adj.get(e.source).push(e.target)
  }
  const queue = start ? [[start.id, 0]] : []
  while (queue.length) {
    const [id, d] = queue.shift()
    if (depth.has(id)) continue
    depth.set(id, d)
    for (const nxt of adj.get(id) || []) queue.push([nxt, d + 1])
  }
  const rowCount = new Map()
  nodes.forEach((n) => {
    const d = depth.get(n.id) ?? 0
    const row = rowCount.get(d) || 0
    rowCount.set(d, row + 1)
    pos.set(n.id, { x: 80 + d * 260, y: 60 + row * 110 })
  })
  return { pos, rebuilt: true }
}

/**
 * v1 图 → Schema v2
 * @param {import('./index.js').V1Graph} v1Graph Agent.graph_definition
 * @param {{name?:string}} [options]
 * @returns {import('./index.js').ConvertResult}
 */
export function convertV1ToV2(v1Graph, options = {}) {
  const issues = []
  const report = createReport()

  // ---- 输入归一（整图级失败：graph=null）----
  if (!v1Graph || typeof v1Graph !== 'object' || !Array.isArray(v1Graph.nodes)) {
    return {
      graph: null,
      issues: [makeWarn('W-201', 'v1 图结构非法：缺少 nodes 数组')],
      report
    }
  }
  const v1Nodes = v1Graph.nodes
  const v1Edges = Array.isArray(v1Graph.edges) ? v1Graph.edges : []
  if (!Array.isArray(v1Graph.edges)) {
    issues.push(makeWarn('W-203', 'v1 图缺少 edges 数组，按空边处理'))
  }

  const { pos, rebuilt } = layoutPositions(v1Nodes, v1Edges)
  if (rebuilt) issues.push(makeWarn('W-204', 'v1 图无位置信息，已按层次布局重建'))

  // ---- 节点转换 ----
  const nodes = []
  const nodeTypeById = new Map()
  const degradedIds = new Set()
  for (const vn of v1Nodes) {
    if (!vn?.id || !vn?.type) {
      addNodeDiff(report, { nodeId: vn?.id || '(unknown)', v1Type: vn?.type || '(unknown)', v2Type: null, status: 'failed' })
      issues.push(makeWarn('W-201', `节点缺少 id/type，已跳过：${JSON.stringify(vn)?.slice(0, 80)}`))
      continue
    }
    const rule = V1_NODE_MAPPING[vn.type]
    const data = vn.data || {}
    if (!rule) {
      // 未知类型：degraded 保留
      degradedIds.add(vn.id)
      nodeTypeById.set(vn.id, vn.type)
      nodes.push({
        id: vn.id, type: vn.type, position: pos.get(vn.id),
        data: { label: data.label || vn.type, config: { ...data } }
      })
      addNodeDiff(report, { nodeId: vn.id, v1Type: vn.type, v2Type: null, status: 'degraded' })
      issues.push(makeWarn('W-201', `未知节点类型 ${vn.type}，已原样保留待人工处理`, { nodeId: vn.id }))
      continue
    }
    if (rule.v2Type === null) {
      // 已知但不支持：degraded 保留原类型与 config 原文
      degradedIds.add(vn.id)
      nodeTypeById.set(vn.id, vn.type)
      nodes.push({
        id: vn.id, type: vn.type, position: pos.get(vn.id),
        data: { label: data.label || vn.type, config: { ...data } }
      })
      addNodeDiff(report, { nodeId: vn.id, v1Type: vn.type, v2Type: null, status: 'degraded' })
      issues.push(makeWarn('W-201', `节点类型 ${vn.type} 在 Schema v2 用户域无对应语义，已降级保留`, { nodeId: vn.id }))
      continue
    }
    // converted
    const { config, dropped } = rule.mapConfig(data)
    nodeTypeById.set(vn.id, rule.v2Type)
    nodes.push({
      id: vn.id, type: rule.v2Type, position: pos.get(vn.id),
      data: { label: data.label || getNodeMeta(rule.v2Type)?.label || rule.v2Type, config }
    })
    addNodeDiff(report, {
      nodeId: vn.id, v1Type: vn.type, v2Type: rule.v2Type, status: 'converted',
      ...(dropped.length ? { droppedFields: dropped } : {})
    })
    for (const f of dropped) {
      issues.push(makeWarn('W-202', `字段 ${vn.type}.${f} 在 v2 无对应语义，已记录未迁移`, { nodeId: vn.id, field: f }))
    }
  }

  // ---- 边转换：补齐 handle；degraded 节点的边跳过（端口不可知，W-203）----
  const edges = []
  for (const ve of v1Edges) {
    const eid = `e_${ve.source}__${ve.target}`
    if (!ve.source || !ve.target) {
      addEdgeDiff(report, { edge: JSON.stringify(ve), status: 'failed', reason: '缺少 source/target' })
      continue
    }
    if (degradedIds.has(ve.source) || degradedIds.has(ve.target)) {
      addEdgeDiff(report, { edge: eid, status: 'skipped', reason: '端点为降级节点，待人工重连' })
      issues.push(makeWarn('W-203', `边 ${ve.source}→${ve.target} 涉及降级节点，已跳过待人工重连`, { edgeId: eid }))
      continue
    }
    const srcType = nodeTypeById.get(ve.source)
    const dstType = nodeTypeById.get(ve.target)
    let sourceHandle
    if (srcType === 'condition') {
      sourceHandle = mapConditionBranch(ve.condition)
      issues.push(makeWarn('W-203', `条件出边 ${ve.source}→${ve.target} 分支按${sourceHandle === 'true' ? '真' : '假'}处理，请人工核对`, { edgeId: eid }))
    } else {
      sourceHandle = DEFAULT_SOURCE_HANDLE[srcType] || getNodeMeta(srcType)?.outputs?.[0]?.name
    }
    const targetHandle = DEFAULT_TARGET_HANDLE[dstType] || getNodeMeta(dstType)?.inputs?.[0]?.name
    if (!sourceHandle || !targetHandle) {
      addEdgeDiff(report, { edge: eid, status: 'failed', reason: `端口不可判定（${srcType}/${dstType}）` })
      issues.push(makeWarn('W-203', `边 ${ve.source}→${ve.target} 端口不可判定，已跳过`, { edgeId: eid }))
      continue
    }
    const edge = { id: eid, source: ve.source, sourceHandle, target: ve.target, targetHandle }
    if (srcType === 'condition' && ve.condition) edge.condition = ve.condition
    edges.push(edge)
    addEdgeDiff(report, { edge: eid, status: 'converted' })
  }

  // ---- 组装 Schema v2 ----
  const graph = {
    schema_version: 2,
    meta: {
      name: options.name || 'v1 转换工作流',
      description: '',
      icon: '',
      converted_from: 'v1',
      conversion: { converted: report.summary.converted, degraded: report.summary.degraded, failed: report.summary.failed }
    },
    variables: [],
    nodes,
    edges,
    settings: { timeout_s: 300, retry: { max: 1, backoff: 'exponential' }, trace_level: 'standard', memory_mode: 'off' }
  }

  // ---- 校验闭环：E-1xx 并入 issues ----
  const validationIssues = validateGraph(graph)

  return { graph, issues: [...issues, ...validationIssues], report }
}
