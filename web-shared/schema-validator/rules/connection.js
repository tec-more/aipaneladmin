/**
 * 连线期校验（拖动松开时实时执行，PRD C3/C4）
 * 溯源：PRD §4.4/§4.5；graph_validator.py 边相关规则。
 * 规则顺序：存在性 → start/end 方向 → 自连 E-103 → 重复 E-104 → 占用 E-105 → 类型 E-101 → 环 E-103。
 */
import { typesCompatible } from '../types.js'
import { getNodeMeta, resolvePortType } from '../nodeRegistry.js'
import { makeIssue } from './codes.js'

function findNode(graph, id) {
  return (graph.nodes || []).find((n) => n.id === id) || null
}

/**
 * 加边后是否成环：从 target 沿出边 DFS 能否回到 source
 * @param {Object[]} nodes @param {Object[]} edges
 * @param {string} source @param {string} target
 * @param {Array<{source:string,target:string}>} extraEdges 尚未入图的候选边
 */
export function wouldCreateCycle(nodes, edges, source, target, extraEdges = []) {
  const adj = new Map()
  const all = edges.concat(extraEdges)
  for (const e of all) {
    if (!adj.has(e.source)) adj.set(e.source, [])
    adj.get(e.source).push(e.target)
  }
  const visited = new Set()
  const stack = [target]
  while (stack.length) {
    const cur = stack.pop()
    if (cur === source) return true
    if (visited.has(cur)) continue
    visited.add(cur)
    for (const nxt of adj.get(cur) || []) stack.push(nxt)
  }
  return false
}

/**
 * 连线期单条校验
 * @param {import('../index.js').GraphV2} graph 当前图
 * @param {{source:string, sourceHandle:string, target:string, targetHandle:string}} conn 候选连接
 * @returns {import('../index.js').ValidationIssue|null} null 表示可连
 */
export function validateConnection(graph, conn) {
  const { source, sourceHandle, target, targetHandle } = conn
  const srcNode = findNode(graph, source)
  const dstNode = findNode(graph, target)
  if (!srcNode || !dstNode) {
    return makeIssue('E-103', '连线端点不存在', { edgeId: `${source}->${target}` })
  }

  // start 不允许入边 / end 不允许出边（PRD §5.1；4.8）
  if (getNodeMeta(dstNode.type)?.type === 'start') {
    return makeIssue('E-103', '开始节点不允许连入边', { nodeId: target })
  }
  if (getNodeMeta(srcNode.type)?.type === 'end') {
    return makeIssue('E-103', '结束节点不允许连出边', { nodeId: source })
  }

  // E-103 自连（PRD 4.4 禁止自连）
  if (source === target) {
    return makeIssue('E-103', '节点不能连接自身', { nodeId: source })
  }

  // E-104 重复连线（同一 source_handle → target_handle 只允许一条）
  const dup = (graph.edges || []).some(
    (e) => e.source === source && e.sourceHandle === sourceHandle &&
           e.target === target && e.targetHandle === targetHandle
  )
  if (dup) {
    return makeIssue('E-104', '已存在相同连线', { nodeId: target })
  }

  // E-105 输入端已占用（输入端口单入；条件分支每出端口至多 1 条）
  const occupied = (graph.edges || []).some(
    (e) => e.target === target && e.targetHandle === targetHandle
  )
  if (occupied) {
    return makeIssue('E-105', '该输入端已有连线，可先删除原连线', { nodeId: target })
  }
  const branchBusy = (graph.edges || []).some(
    (e) => e.source === source && e.sourceHandle === sourceHandle &&
           getNodeMeta(srcNode.type)?.type === 'condition'
  )
  if (branchBusy) {
    return makeIssue('E-105', '条件分支端口至多 1 条出边', { nodeId: source })
  }

  // E-101 类型兼容（C3 拖动中实时提示同源规则）
  const srcType = resolvePortType(srcNode, 'outputs', sourceHandle)
  const dstType = resolvePortType(dstNode, 'inputs', targetHandle)
  if (srcType == null || dstType == null) {
    return makeIssue('E-101', `端口不存在：${srcType == null ? `${source}.${sourceHandle}` : `${target}.${targetHandle}`}`, { nodeId: target })
  }
  if (!typesCompatible(srcType, dstType)) {
    return makeIssue('E-101', `类型不兼容：${srcType} → ${dstType}`, { nodeId: target })
  }

  // E-103 成环（非循环容器内，PRD 4.4）
  if (wouldCreateCycle(graph.nodes || [], graph.edges || [], source, target, [conn])) {
    return makeIssue('E-103', '该连线会形成环', { nodeId: source })
  }

  return null
}
