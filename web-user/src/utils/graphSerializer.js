/**
 * Schema v2 ↔ VueFlow 双向序列化（T8）
 * 架构 04 §3：Schema v2 字段与 VueFlow 完全同构（id/type/position/data 直映射），
 * 转换零字段更名，round-trip 无损。
 * 画布统一以 'wf-node' 渲染（BaseNode 配置驱动），原始节点类型存 data.nodeType。
 */
import { getNodeMeta } from '@validator'

/** 画布内统一渲染组件类型 */
export const WF_NODE_TYPE = 'wf-node'

/**
 * Schema v2 图 → VueFlow 元素
 * @param {import('@validator').GraphV2} graph
 * @returns {{nodes: Object[], edges: Object[]}}
 */
export function toVueFlow(graph) {
  const nodes = (graph?.nodes || []).map((n) => ({
    id: n.id,
    type: WF_NODE_TYPE,
    position: { x: n.position?.x ?? 0, y: n.position?.y ?? 0 },
    data: {
      // 原样保留 Schema v2 data 载荷（label/config/inputs/outputs），并附渲染元数据
      nodeType: n.type,
      label: n.data?.label ?? '',
      config: n.data?.config ?? {},
      inputs: Array.isArray(n.data?.inputs) ? n.data.inputs : undefined,
      outputs: Array.isArray(n.data?.outputs) ? n.data.outputs : undefined
    }
  }))
  const edges = (graph?.edges || []).map((e) => ({
    id: e.id,
    source: e.source,
    sourceHandle: e.sourceHandle,
    target: e.target,
    targetHandle: e.targetHandle,
    // 渲染态字段：直角圆角折线（不写入 Schema v2，toGraph 不回传）
    type: 'smoothstep',
    ...(e.condition ? { condition: e.condition, label: e.condition } : {})
  }))
  return { nodes, edges }
}

/**
 * VueFlow 元素 → Schema v2 图（data 载荷原样回写，剔除渲染态字段）
 * @param {Object[]} vueNodes @param {Object[]} vueEdges
 * @param {{name:string, description?:string, icon?:string}} meta
 * @param {import('@validator').VariableV2[]} variables
 * @param {Object} settings
 * @returns {import('@validator').GraphV2}
 */
export function toGraph(vueNodes, vueEdges, meta, variables, settings) {
  const nodes = (vueNodes || []).map((n) => {
    const data = {
      label: n.data?.label ?? '',
      config: n.data?.config ?? {}
    }
    if (Array.isArray(n.data?.inputs)) data.inputs = n.data.inputs
    if (Array.isArray(n.data?.outputs)) data.outputs = n.data.outputs
    return {
      id: n.id,
      type: n.data?.nodeType || n.type,
      position: { x: Math.round(n.position?.x ?? 0), y: Math.round(n.position?.y ?? 0) },
      data
    }
  })
  const edges = (vueEdges || []).map((e) => {
    const edge = {
      id: e.id,
      source: e.source,
      sourceHandle: e.sourceHandle,
      target: e.target,
      targetHandle: e.targetHandle
    }
    if (e.condition) edge.condition = e.condition
    return edge
  })
  return {
    schema_version: 2,
    meta: { name: meta?.name || '未命名工作流', description: meta?.description || '', icon: meta?.icon || '' },
    variables: variables || [],
    nodes,
    edges,
    settings: settings || { timeout_s: 300, retry: { max: 1, backoff: 'exponential' }, trace_level: 'standard', memory_mode: 'off' }
  }
}

/**
 * 按节点类型生成新节点（注册表驱动，端口/默认config 深拷贝）
 * @param {string} nodeType @param {{x:number,y:number}} position
 * @param {number} seq 序号（生成可读 id/label）
 * @returns {Object} VueFlow 节点
 */
export function createNodeByType(nodeType, position, seq = 1) {
  const meta = getNodeMeta(nodeType)
  if (!meta) throw new Error(`未知节点类型: ${nodeType}`)
  return {
    id: `${nodeType}_${Date.now().toString(36)}_${seq}`,
    type: WF_NODE_TYPE,
    position: { x: Math.round(position.x), y: Math.round(position.y) },
    data: {
      nodeType,
      label: `${meta.label} ${seq}`,
      config: JSON.parse(JSON.stringify(meta.defaultConfig || {}))
    }
  }
}

/**
 * 生成边 id（稳定格式，便于 E-104 重复判定排查）
 */
export function makeEdgeId(conn) {
  return `e_${conn.source}_${conn.sourceHandle}__${conn.target}_${conn.targetHandle}`
}
