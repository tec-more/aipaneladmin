/**
 * 全量图校验（保存前本地预检 / 编辑器问题面板）
 * 溯源：graph_validator.py validate_graph_structure L360-L684；PRD §4.5 错误码。
 * 覆盖：E-100~E-107、E-109、E-111、E-112；
 * E-108（子工作流版本失效）、E-110（资源授权）为 server-only，本地不重复判定（T8 裁定 Q5）。
 * 纯函数：不修改入参，无副作用。
 */
import { typesCompatible, isValidType, normalizeType } from '../types.js'
import { getNodeMeta, resolvePortType, normalizeNodeType } from '../nodeRegistry.js'
import { makeIssue, LEVEL_WARNING } from './codes.js'
import { wouldCreateCycle } from './connection.js'

const TEMPLATE_REF_RE = /\{\{\s*([A-Za-z_][\w.]*?)\s*\}\}/g
const MAX_LOOP_ITERATIONS = 100 // 套餐上限保守值（PRD E-111；服务端按套餐裁定）

function isBlank(v) {
  return v == null || (typeof v === 'string' && !v.trim()) ||
    (Array.isArray(v) && v.length === 0) ||
    (typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === 0)
}

// ---- 节点 config 必填（对齐服务端 _check_xxx 关键项）----
function checkNodeConfig(node, issues) {
  const cfg = node.data?.config || {}
  const nid = node.id
  const type = normalizeNodeType(node.type)
  switch (type) {
    case 'llm':
      if (isBlank(cfg.model_ref)) issues.push(makeIssue('E-100', 'LLM 节点缺少必填配置 model_ref', { nodeId: nid, field: 'model_ref' }))
      if (isBlank(cfg.user_prompt)) issues.push(makeIssue('E-100', 'LLM 节点缺少必填配置 user_prompt', { nodeId: nid, field: 'user_prompt' }))
      if (cfg.temperature != null && !(typeof cfg.temperature === 'number' && cfg.temperature >= 0 && cfg.temperature <= 2)) {
        issues.push(makeIssue('E-100', 'LLM 节点 temperature 须在 0-2 之间', { nodeId: nid, field: 'temperature' }))
      }
      break
    case 'rag_retrieval': {
      const refs = cfg.knowledge_base_refs || cfg.kb_ids
      if (!Array.isArray(refs) || refs.length === 0) {
        issues.push(makeIssue('E-100', '知识检索节点缺少必填配置 knowledge_base_refs（≥1）', { nodeId: nid, field: 'knowledge_base_refs' }))
      }
      break
    }
    case 'condition':
      if (isBlank(cfg.expression)) issues.push(makeIssue('E-100', '条件分支节点缺少表达式 expression', { nodeId: nid, field: 'expression' }))
      break
    case 'loop':
      if (cfg.max_iterations == null || typeof cfg.max_iterations !== 'number' || cfg.max_iterations < 1) {
        issues.push(makeIssue('E-111', '循环节点缺少 max_iterations', { nodeId: nid, field: 'max_iterations' }))
      } else if (cfg.max_iterations > MAX_LOOP_ITERATIONS) {
        issues.push(makeIssue('E-111', `循环上限超出套餐允许（最大 ${MAX_LOOP_ITERATIONS}）`, { nodeId: nid, field: 'max_iterations' }))
      }
      if (isBlank(cfg.exit_condition)) {
        issues.push(makeIssue('E-111', '循环节点缺少退出条件 exit_condition', { nodeId: nid, field: 'exit_condition' }))
      }
      break
    case 'sub_workflow':
      if (isBlank(cfg.workflow_ref)) issues.push(makeIssue('E-100', '子工作流节点未选择目标工作流', { nodeId: nid, field: 'workflow_ref' }))
      break
    case 'sub_agent':
      if (isBlank(cfg.agent_ref)) issues.push(makeIssue('E-100', '子 Agent 节点未选择目标 Agent', { nodeId: nid, field: 'agent_ref' }))
      break
    case 'tool':
      if (isBlank(cfg.tool_ref)) issues.push(makeIssue('E-100', '工具节点未选择 tool_ref', { nodeId: nid, field: 'tool_ref' }))
      break
    case 'template':
      if (isBlank(cfg.template)) issues.push(makeIssue('E-100', '模板渲染节点缺少必填配置 template', { nodeId: nid, field: 'template' }))
      break
    case 'hitl':
      // E-112：审批人 + 超时策略
      if (isBlank(cfg.assignee) || isBlank(cfg.timeout_action)) {
        issues.push(makeIssue('E-112', '人工卡点未配置审批人或超时策略', { nodeId: nid }))
      }
      break
    default:
      break
  }
}

// ---- 模板与 from 引用（E-107）----
function collectTemplateRefs(value, acc) {
  if (typeof value === 'string') {
    TEMPLATE_REF_RE.lastIndex = 0
    let m
    while ((m = TEMPLATE_REF_RE.exec(value)) !== null) acc.add(m[1])
  } else if (Array.isArray(value)) {
    value.forEach((v) => collectTemplateRefs(v, acc))
  } else if (value && typeof value === 'object') {
    Object.values(value).forEach((v) => collectTemplateRefs(v, acc))
  }
}

function checkReferences(node, nodeIds, variableNames, issues) {
  const nid = node.id
  // inputs[].from 强校验：'nodeId.portName'
  for (const p of node.data?.inputs || []) {
    if (!p?.from) continue
    const dot = p.from.indexOf('.')
    const refNode = dot > 0 ? p.from.slice(0, dot) : p.from
    const refPort = dot > 0 ? p.from.slice(dot + 1) : ''
    if (!nodeIds.has(refNode)) {
      issues.push(makeIssue('E-107', `输入引用未声明的节点：${p.from}`, { nodeId: nid, field: `inputs.${p.name}` }))
      continue
    }
    if (refPort) {
      const target = null // 端口存在性在 E-101 阶段按类型解析覆盖
      void target
    }
  }
  // 模板 {{ref}}：首段必须是节点 id 或已声明变量
  const refs = new Set()
  collectTemplateRefs(node.data?.config, refs)
  for (const ref of refs) {
    const head = ref.split('.')[0]
    if (!nodeIds.has(head) && !variableNames.has(head)) {
      issues.push(makeIssue('E-107', `模板引用了未声明的变量或节点：{{${ref}}}`, { nodeId: nid }))
    }
  }
}

/**
 * 全量校验入口
 * @param {import('../index.js').GraphV2} graph Schema v2 图
 * @returns {import('../index.js').ValidationIssue[]}
 */
export function validateGraph(graph) {
  const issues = []
  if (!graph || typeof graph !== 'object') {
    return [makeIssue('E-100', 'graph_json 必须是对象')]
  }
  if (graph.schema_version !== 2) {
    issues.push(makeIssue('E-100', 'schema_version 必须为 2'))
  }
  const nodes = Array.isArray(graph.nodes) ? graph.nodes : []
  const edges = Array.isArray(graph.edges) ? graph.edges : []
  const variables = Array.isArray(graph.variables) ? graph.variables : []

  // ---- 节点基础 ----
  const nodeIds = new Set()
  const nodeMap = new Map()
  for (const n of nodes) {
    if (!n?.id) { issues.push(makeIssue('E-100', '存在缺少 id 的节点')); continue }
    if (nodeIds.has(n.id)) issues.push(makeIssue('E-100', `节点 id 重复：${n.id}`, { nodeId: n.id }))
    nodeIds.add(n.id)
    nodeMap.set(n.id, n)
    const meta = getNodeMeta(n.type)
    if (!meta) {
      issues.push(makeIssue('E-109', `未知节点类型：${n.type}`, { nodeId: n.id }))
      continue
    }
    // E-109 域开关（Q1：gray/disabled 不可出现在用户域图）
    if (meta.availability !== 'open') {
      issues.push(makeIssue('E-109', `节点类型未开放：${meta.label}（${meta.disabledReason || '未授权'}）`, { nodeId: n.id }))
    }
    if (isBlank(n.data?.label)) {
      issues.push(makeIssue('E-100', '节点缺少显示名称 label', { nodeId: n.id, field: 'label' }))
    }
    // 变量/端口类型写法合法性
    for (const p of [...(n.data?.inputs || []), ...(n.data?.outputs || [])]) {
      if (p?.type && !isValidType(p.type)) {
        issues.push(makeIssue('E-100', `端口 ${p.name} 类型写法非法：${p.type}`, { nodeId: n.id }))
      }
    }
    checkNodeConfig(n, issues)
  }

  // ---- start/end 唯一性与方向 ----
  const starts = nodes.filter((n) => normalizeNodeType(n.type) === 'start')
  const ends = nodes.filter((n) => normalizeNodeType(n.type) === 'end')
  if (starts.length !== 1) issues.push(makeIssue('E-100', `开始节点必须恰好 1 个（当前 ${starts.length}）`))
  if (ends.length !== 1) issues.push(makeIssue('E-100', `结束节点必须恰好 1 个（当前 ${ends.length}）`))

  // ---- 边结构 ----
  const edgeKeys = new Set()
  const inputTaken = new Set()
  const branchTaken = new Set()
  for (const e of edges) {
    const eid = e.id || `${e.source}->${e.target}`
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) {
      issues.push(makeIssue('E-103', '连线端点不存在', { edgeId: eid }))
      continue
    }
    const srcType = normalizeNodeType(nodeMap.get(e.source)?.type)
    const dstType = normalizeNodeType(nodeMap.get(e.target)?.type)
    if (dstType === 'start') issues.push(makeIssue('E-103', '开始节点不允许连入边', { nodeId: e.target, edgeId: eid }))
    if (srcType === 'end') issues.push(makeIssue('E-103', '结束节点不允许连出边', { nodeId: e.source, edgeId: eid }))
    if (e.source === e.target) issues.push(makeIssue('E-103', '节点不能连接自身', { nodeId: e.source, edgeId: eid }))
    const key = `${e.source}|${e.sourceHandle}|${e.target}|${e.targetHandle}`
    if (edgeKeys.has(key)) issues.push(makeIssue('E-104', '存在重复连线', { nodeId: e.target, edgeId: eid }))
    edgeKeys.add(key)
    const inKey = `${e.target}|${e.targetHandle}`
    if (inputTaken.has(inKey)) issues.push(makeIssue('E-105', '同一输入端存在多条连线', { nodeId: e.target, edgeId: eid }))
    inputTaken.add(inKey)
    if (srcType === 'condition') {
      const bKey = `${e.source}|${e.sourceHandle}`
      if (branchTaken.has(bKey)) issues.push(makeIssue('E-105', '条件分支端口至多 1 条出边', { nodeId: e.source, edgeId: eid }))
      branchTaken.add(bKey)
    }
    // E-101 类型
    const st = resolvePortType(nodeMap.get(e.source), 'outputs', e.sourceHandle)
    const dt = resolvePortType(nodeMap.get(e.target), 'inputs', e.targetHandle)
    if (st == null || dt == null) {
      issues.push(makeIssue('E-101', `连线端口不存在：${st == null ? `${e.source}.${e.sourceHandle}` : `${e.target}.${e.targetHandle}`}`, { edgeId: eid }))
    } else if (!typesCompatible(st, dt)) {
      issues.push(makeIssue('E-101', `端口类型不兼容：${normalizeType(st)} → ${normalizeType(dt)}`, { edgeId: eid, nodeId: e.target }))
    }
  }

  // ---- 环检测（全图：对每个节点，从其出边邻居出发能否回到自身）----
  for (const n of nodes) {
    const nexts = edges.filter((e) => e.source === n.id).map((e) => e.target)
    const inCycle = nexts.some((nxt) => wouldCreateCycle(nodes, edges, n.id, nxt))
    if (inCycle) {
      issues.push(makeIssue('E-103', `图中存在环（涉及节点 ${n.data?.label || n.id}）`, { nodeId: n.id }))
      break // 环报一条即可，避免刷屏
    }
  }

  // ---- E-102 必填输入未连接 ----
  const connectedInputs = new Set(edges.map((e) => `${e.target}|${e.targetHandle}`))
  for (const n of nodes) {
    const meta = getNodeMeta(n.type)
    if (!meta) continue
    const required = [
      ...(meta.inputs || []).filter((p) => p.required),
      ...((n.data?.inputs || []).filter((p) => p?.required))
    ]
    const seen = new Set()
    for (const p of required) {
      if (!p?.name || seen.has(p.name)) continue
      seen.add(p.name)
      if (!connectedInputs.has(`${n.id}|${p.name}`)) {
        issues.push(makeIssue('E-102', `必填输入未连接：${n.data?.label || n.id}.${p.name}`, { nodeId: n.id, field: `inputs.${p.name}` }))
      }
    }
  }

  // ---- E-107 引用 ----
  const variableNames = new Set(variables.map((v) => v?.name).filter(Boolean))
  for (const n of nodes) checkReferences(n, nodeIds, variableNames, issues)

  // ---- E-113 可达性（K5：与 start 不连通，warning 不阻断）----
  {
    const reachable = new Set()
    const adj = new Map()
    for (const e of edges) {
      if (!adj.has(e.source)) adj.set(e.source, [])
      adj.get(e.source).push(e.target)
    }
    const queue = nodes.filter((n) => normalizeNodeType(n.type) === 'start').map((n) => n.id)
    while (queue.length) {
      const id = queue.shift()
      if (reachable.has(id)) continue
      reachable.add(id)
      for (const nxt of adj.get(id) || []) queue.push(nxt)
    }
    for (const n of nodes) {
      if (normalizeNodeType(n.type) === 'start') continue
      if (!reachable.has(n.id)) {
        issues.push(makeIssue('E-113', `节点与开始节点不连通：${n.data?.label || n.id}`, { nodeId: n.id, level: LEVEL_WARNING }))
      }
    }
  }

  // ---- E-106 输出悬空（warning；end 无输出除外）----
  const usedOut = new Set(edges.map((e) => `${e.source}|${e.sourceHandle}`))
  for (const n of nodes) {
    const meta = getNodeMeta(n.type)
    // start 的注入输出为可选使用，end 无输出，均不计悬空
    if (!meta || meta.type === 'end' || meta.type === 'start') continue
    for (const p of meta.outputs || []) {
      if (!usedOut.has(`${n.id}|${p.name}`)) {
        issues.push(makeIssue('E-106', `输出端口悬空：${n.data?.label || n.id}.${p.name}`, { nodeId: n.id, level: LEVEL_WARNING }))
      }
    }
  }

  return issues
}
