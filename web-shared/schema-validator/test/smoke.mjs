/**
 * 校验器冒烟测试（T8 节点4；T9 复用回归）
 * 运行：node test/smoke.mjs
 * 覆盖：类型矩阵边界 + 连线期规则 + 全量校验各错误码。
 */
import { typesCompatible, validateConnection, validateGraph } from '../index.js'

let pass = 0
let fail = 0
function t(name, cond) {
  if (cond) { pass += 1 } else { fail += 1; console.error(`  FAIL: ${name}`) }
}

// ============ 1. 类型兼容矩阵（对齐服务端 types_compatible）============
t('同型直连', typesCompatible('string', 'string'))
t('integer→number 加宽', typesCompatible('integer', 'number'))
t('number 不可收窄 integer', !typesCompatible('number', 'integer'))
t('任意→any 透传', typesCompatible('string', 'any'))
t('any→具体禁止', !typesCompatible('any', 'string'))
t('unknown 全禁', !typesCompatible('unknown', 'any') && !typesCompatible('any', 'unknown') && !typesCompatible('string', 'unknown'))
t('array 元素兼容', typesCompatible('array<integer>', 'array<number>'))
t('chunk[] 归一 array<chunk>', typesCompatible('chunk[]', 'array<chunk>'))
t('array 元素不兼容', !typesCompatible('array<string>', 'array<number>'))
t('message[] 归一', typesCompatible('message[]', 'array<message>'))

// ============ 2. 图构造工具 ============
function node(id, type, data = {}, position = { x: 0, y: 0 }) {
  return { id, type, position, data: { label: data.label || id, config: data.config || {}, ...(data.inputs ? { inputs: data.inputs } : {}), ...(data.outputs ? { outputs: data.outputs } : {}) } }
}
function edge(id, source, sourceHandle, target, targetHandle) {
  return { id, source, sourceHandle, target, targetHandle }
}
/** 合法基线图：start → llm → end（应 0 error） */
function baseGraph() {
  return {
    schema_version: 2,
    meta: { name: 'smoke' },
    variables: [],
    nodes: [
      node('n1', 'start'),
      node('n2', 'llm', { config: { model_ref: 'm1', user_prompt: '{{n1.user_input}}' } }, { x: 300, y: 0 }),
      node('n3', 'end', {}, { x: 600, y: 0 })
    ],
    edges: [
      edge('e1', 'n1', 'user_input', 'n2', 'query'),
      edge('e2', 'n2', 'text', 'n3', 'answer')
    ],
    settings: {}
  }
}
const errors = (issues) => issues.filter((i) => i.level === 'error')
const codesOf = (issues) => new Set(issues.map((i) => i.code))

// ============ 3. 全量校验：基线 ============
{
  const issues = validateGraph(baseGraph())
  t('基线图 0 error', errors(issues).length === 0)
}

// ============ 4. 全量校验：错误码覆盖 ============
{
  // E-100：llm 缺 model_ref / user_prompt；schema_version 错
  const g = baseGraph()
  g.nodes[1].data.config = { model_ref: '', user_prompt: '' }
  t('E-100 llm 必填缺失', codesOf(validateGraph(g)).has('E-100'))
  const g2 = baseGraph(); g2.schema_version = 1
  t('E-100 schema_version', codesOf(validateGraph(g2)).has('E-100'))
}
{
  // E-101：类型不兼容（自定义端口 string→number）
  const g = baseGraph()
  g.nodes.push(node('n4', 'llm', { config: { model_ref: 'm', user_prompt: 'x' }, inputs: [{ name: 'input', type: 'number' }] }))
  g.edges.push(edge('e3', 'n1', 'session_id', 'n4', 'input'))
  t('E-101 类型不兼容', codesOf(validateGraph(g)).has('E-101'))
}
{
  // E-102：rag 必填 query 未连
  const g = baseGraph()
  g.nodes.push(node('n4', 'rag_retrieval', { config: { knowledge_base_refs: ['kb1'] } }))
  t('E-102 必填未连接', codesOf(validateGraph(g)).has('E-102'))
}
{
  // E-103：自连 + 成环
  const g = baseGraph()
  g.edges.push(edge('e3', 'n2', 'text', 'n2', 'query'))
  t('E-103 自连', codesOf(validateGraph(g)).has('E-103'))
  const g2 = baseGraph()
  g2.nodes.push(node('n4', 'condition', { config: { expression: 'x' } }))
  g2.edges.push(edge('e3', 'n2', 'text', 'n4', 'input'), edge('e4', 'n4', 'true', 'n2', 'query'))
  t('E-103 成环', codesOf(validateGraph(g2)).has('E-103'))
  // start 入边
  const g3 = baseGraph()
  g3.edges.push(edge('e3', 'n2', 'text', 'n1', 'user_input'))
  t('E-103 start 入边', codesOf(validateGraph(g3)).has('E-103'))
}
{
  // E-104：重复连线
  const g = baseGraph()
  g.edges.push(edge('e3', 'n1', 'user_input', 'n2', 'query'))
  t('E-104 重复', codesOf(validateGraph(g)).has('E-104'))
}
{
  // E-105：输入端占用（两源同输入）
  const g = baseGraph()
  g.nodes.push(node('n4', 'llm', { config: { model_ref: 'm', user_prompt: 'x' } }))
  g.edges.push(edge('e3', 'n4', 'text', 'n2', 'query'))
  t('E-105 输入占用', codesOf(validateGraph(g)).has('E-105'))
  // 条件分支端口占用
  const g2 = baseGraph()
  g2.nodes.push(node('n4', 'condition', { config: { expression: 'x' } }), node('n5', 'llm', { config: { model_ref: 'm', user_prompt: 'x' } }))
  g2.edges.push(edge('e3', 'n2', 'text', 'n4', 'input'), edge('e4', 'n4', 'true', 'n3', 'answer'), edge('e5', 'n4', 'true', 'n5', 'query'))
  t('E-105 分支占用', codesOf(validateGraph(g2)).has('E-105'))
}
{
  // E-106：输出悬空（warning）
  const g = baseGraph()
  g.nodes.push(node('n4', 'rag_retrieval', { config: { knowledge_base_refs: ['kb1'] } }))
  g.edges.push(edge('e3', 'n1', 'user_input', 'n4', 'query'))
  const issues = validateGraph(g)
  t('E-106 悬空 warning', issues.some((i) => i.code === 'E-106' && i.level === 'warning'))
  t('E-106 不计 start 注入输出', !issues.some((i) => i.code === 'E-106' && i.node_id === 'n1'))
}
{
  // E-107：模板引用未声明
  const g = baseGraph()
  g.nodes[1].data.config.user_prompt = '{{ghost_node.x}}'
  t('E-107 未声明引用', codesOf(validateGraph(g)).has('E-107'))
}
{
  // E-109：未开放节点类型（code 永久禁 / hitl gray）
  const g = baseGraph()
  g.nodes.push(node('n4', 'code'))
  t('E-109 code 禁用', codesOf(validateGraph(g)).has('E-109'))
  const g2 = baseGraph()
  g2.nodes.push(node('n4', 'hitl', { config: { assignee: 'u1', timeout_action: 'fail' } }))
  t('E-109 hitl 置灰', codesOf(validateGraph(g2)).has('E-109'))
}
{
  // E-111：循环超限 / 缺退出条件
  const g = baseGraph()
  g.nodes.push(node('n4', 'loop', { config: { max_iterations: 200, exit_condition: 'done' } }))
  t('E-111 超限', codesOf(validateGraph(g)).has('E-111'))
  const g2 = baseGraph()
  g2.nodes.push(node('n4', 'loop', { config: { max_iterations: 10, exit_condition: '' } }))
  t('E-111 缺退出条件', codesOf(validateGraph(g2)).has('E-111'))
}
{
  // E-112：HITL 缺审批人/超时策略
  const g = baseGraph()
  g.nodes.push(node('n4', 'hitl', { config: {} }))
  t('E-112 hitl 配置缺失', codesOf(validateGraph(g)).has('E-112'))
}
{
  // start/end 唯一性
  const g = baseGraph()
  g.nodes.push(node('n4', 'start'))
  t('start 唯一性', errors(validateGraph(g)).some((i) => i.message.includes('开始节点必须恰好 1 个')))
  const g2 = baseGraph()
  g2.nodes = g2.nodes.filter((n) => n.type !== 'end')
  t('end 缺失', errors(validateGraph(g2)).some((i) => i.message.includes('结束节点必须恰好 1 个')))
}

// ============ 5. 连线期校验 ============
{
  const g = baseGraph()
  g.nodes.push(node('n4', 'llm', { config: { model_ref: 'm', user_prompt: 'x' } }))
  t('合法连线放行', validateConnection(g, { source: 'n1', sourceHandle: 'session_id', target: 'n4', targetHandle: 'query' }) === null)
  t('连线 E-104 先于占用命中', validateConnection(g, { source: 'n1', sourceHandle: 'user_input', target: 'n2', targetHandle: 'query' })?.code === 'E-104')
  const gNum = baseGraph()
  gNum.nodes[1].data.inputs = [{ name: 'query', type: 'number' }]
  gNum.edges = gNum.edges.filter((e) => e.id !== 'e1') // 解除占用，隔离出类型规则
  t('连线 E-101', validateConnection(gNum, { source: 'n1', sourceHandle: 'user_input', target: 'n2', targetHandle: 'query' })?.code === 'E-101')
  t('连线 E-103 自连', validateConnection(g, { source: 'n2', sourceHandle: 'text', target: 'n2', targetHandle: 'query' })?.code === 'E-103')
  t('连线 E-103 成环', validateConnection(g, { source: 'n3', sourceHandle: 'answer', target: 'n1', targetHandle: 'x' }) !== null)
  t('连线 E-104 重复', validateConnection(g, { source: 'n2', sourceHandle: 'text', target: 'n3', targetHandle: 'answer' })?.code === 'E-104')
}

// ============ 6. T10：E-113 可达性与 fields 契约 ============
import { getNodeMeta } from '../index.js'
{
  // E-113：与 start 不连通报 warning（K5）
  const g = baseGraph()
  g.nodes.push(node('n4', 'llm', { config: { model_ref: 'm', user_prompt: 'x' } })) // 孤立节点
  const issues = validateGraph(g)
  t('E-113 不连通 warning', issues.some((i) => i.code === 'E-113' && i.level === 'warning' && i.node_id === 'n4'))
  t('E-113 已连通节点不报', !issues.some((i) => i.code === 'E-113' && i.node_id === 'n2'))
  t('基线图无 E-113', !validateGraph(baseGraph()).some((i) => i.code === 'E-113'))
}
{
  // fields 契约：open 节点表单声明存在且 required 与 E-100 对齐
  const llm = getNodeMeta('llm')
  t('llm fields 声明存在', Array.isArray(llm.fields) && llm.fields.length >= 10)
  t('llm model_ref/user_prompt required', llm.fields.find((f) => f.key === 'model_ref')?.required && llm.fields.find((f) => f.key === 'user_prompt')?.required)
  t('llm 端口含 query/prompt_vars/context/history', ['query', 'prompt_vars', 'context', 'history'].every((p) => llm.inputs.some((i) => i.name === p)))
  t('llm 输出 text/structured/usage/raw', ['text', 'structured', 'usage', 'raw'].every((p) => llm.outputs.some((o) => o.name === p)))
  const rag = getNodeMeta('rag_retrieval')
  t('rag 输出含 citations/empty/stats', ['chunks', 'citations', 'empty', 'stats'].every((p) => rag.outputs.some((o) => o.name === p)))
  t('rag top_k 范围 1-50 默认 8', rag.fields.find((f) => f.key === 'top_k')?.min === 1 && rag.fields.find((f) => f.key === 'top_k')?.max === 50 && rag.fields.find((f) => f.key === 'top_k')?.default === 8)
  t('llm temperature 默认 0.3 范围 0-2', llm.fields.find((f) => f.key === 'temperature')?.default === 0.3 && llm.fields.find((f) => f.key === 'temperature')?.max === 2)
}

console.log(`\nsmoke: ${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)
