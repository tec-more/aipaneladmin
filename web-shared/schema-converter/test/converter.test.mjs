/**
 * 转换器单元测试（T9 节点4 前置自测；node test/converter.test.mjs 直跑）
 * 覆盖：映射矩阵 / 幂等 / 边界 / 校验闭环 / 报告完整性。
 */
import { convertV1ToV2 } from '../index.js'
import {
  FIXTURE_FULL_FLOW, FIXTURE_CONVERTIBLE, FIXTURE_DEGRADED, FIXTURE_COUNT_LOOP, FIXTURE_UNKNOWN_TYPE
} from './fixtures.mjs'

let pass = 0
let fail = 0
function t(name, cond) {
  if (cond) { pass += 1 } else { fail += 1; console.error(`  FAIL: ${name}`) }
}
const errors = (issues) => issues.filter((i) => i.level === 'error')
const warns = (issues) => issues.filter((i) => i.level === 'warning')
const hasCode = (issues, code) => issues.some((i) => i.code === code)
const diffOf = (r, nodeId) => r.report.nodeDiffs.find((d) => d.nodeId === nodeId)

// ============ 1. 后端样例（工作流9）============
{
  const r = convertV1ToV2(FIXTURE_FULL_FLOW, { name: 'wf9' })
  t('wf9 graph 生成', r.graph !== null && r.graph.schema_version === 2)
  t('wf9 start/end converted', diffOf(r, 'start-1')?.status === 'converted' && diffOf(r, 'end-1')?.status === 'converted')
  t('wf9 iteration→loop converted', diffOf(r, 'it-1')?.v2Type === 'loop')
  t('wf9 iteration dropped iterationList/iterationVariable',
    diffOf(r, 'it-1')?.droppedFields?.includes('iterationList') && diffOf(r, 'it-1')?.droppedFields?.includes('iterationVariable'))
  t('wf9 variable_assigner degraded', diffOf(r, 'va-1')?.status === 'degraded' && hasCode(warns(r.issues), 'W-201'))
  t('wf9 output degraded', diffOf(r, 'out-1')?.status === 'degraded')
  t('wf9 降级节点的边跳过 W-203', hasCode(warns(r.issues), 'W-203'))
  t('wf9 无位置信息重建 W-204', hasCode(warns(r.issues), 'W-204'))
  t('wf9 降级节点保留原 config 原文',
    r.graph.nodes.find((n) => n.id === 'va-1')?.data?.config?.variable_name === 'items')
  t('wf9 loop 缺退出条件报 E-111', hasCode(errors(r.issues), 'E-111'))
  t('wf9 降级节点触发 E-109（双源显式）', hasCode(errors(r.issues), 'E-109'))
}

// ============ 2. 全 converted 图 ============
{
  const r = convertV1ToV2(FIXTURE_CONVERTIBLE)
  t('conv 全部 converted', r.report.summary.degraded === 0 && r.report.summary.failed === 0)
  t('conv 校验 0 error', errors(r.issues).length === 0)
  const llm = r.graph.nodes.find((n) => n.id === 'l1')
  t('conv llm model_id→model_ref', llm.data.config.model_ref === 'gpt-4o')
  t('conv llm prompt→user_prompt', llm.data.config.user_prompt === '回答：{{s.user_input}}')
  t('conv llm temperature/max_tokens 直拷', llm.data.config.temperature === 0.5 && llm.data.config.max_tokens === 1024)
  t('conv llm outputVar/skill_ids 记 dropped',
    diffOf(r, 'l1')?.droppedFields?.includes('outputVar') && diffOf(r, 'l1')?.droppedFields?.includes('skill_ids'))
  const tmpl = r.graph.nodes.find((n) => n.id === 't1')
  t('conv template 直映', tmpl.type === 'template' && tmpl.data.config.template === '结果：{{l1.answer}}')
  // 边端口补齐
  const e1 = r.graph.edges.find((e) => e.source === 's')
  const e2 = r.graph.edges.find((e) => e.source === 'l1')
  t('conv 边 handle 补齐', e1.sourceHandle === 'user_input' && e1.targetHandle === 'query' &&
    e2.sourceHandle === 'text' && e2.targetHandle === 'input')
}

// ============ 3. 降级类型集合 ============
{
  const r = convertV1ToV2(FIXTURE_DEGRADED)
  t('degraded 5 类全降级', ['h1', 'c1', 'k1', 'p1', 'a1', 'd1'].every((id) => diffOf(r, id)?.status === 'degraded'))
  t('degraded 保留原类型', r.graph.nodes.find((n) => n.id === 'h1')?.type === 'http')
  t('degraded 原文保留', r.graph.nodes.find((n) => n.id === 'h1')?.data?.config?.url === 'https://a.b/c')
  t('degraded 边跳过（h1→c1 双降级）', r.report.edgeDiffs.some((d) => d.status === 'skipped'))
}

// ============ 4. 计数 loop ============
{
  const r = convertV1ToV2(FIXTURE_COUNT_LOOP)
  const loop = r.graph.nodes.find((n) => n.id === 'lp')
  t('loop loop_count→max_iterations', loop.data.config.max_iterations === 5)
  t('loop mode=count', loop.data.config.mode === 'count')
  t('loop targetHandle=body_in', r.graph.edges.find((e) => e.target === 'lp')?.targetHandle === 'body_in')
}

// ============ 5. 未知类型 ============
{
  const r = convertV1ToV2(FIXTURE_UNKNOWN_TYPE)
  t('unknown degraded 保留', diffOf(r, 'x1')?.status === 'degraded' &&
    r.graph.nodes.find((n) => n.id === 'x1')?.type === 'quantum_node')
}

// ============ 6. 幂等 ============
{
  const a = convertV1ToV2(FIXTURE_FULL_FLOW)
  const b = convertV1ToV2(FIXTURE_FULL_FLOW)
  t('幂等：两次转换产物深度相等', JSON.stringify(a.graph) === JSON.stringify(b.graph))
}

// ============ 7. 边界 ============
{
  t('null 输入 graph=null', convertV1ToV2(null).graph === null)
  t('非对象输入 graph=null', convertV1ToV2('x').graph === null)
  t('缺 nodes graph=null', convertV1ToV2({ edges: [] }).graph === null)
  const r = convertV1ToV2({ nodes: [{ id: 's', type: 'start', data: {} }, { id: 'e', type: 'end', data: {} }] })
  t('缺 edges 按空边 + W-203', r.graph.edges.length === 0 && hasCode(warns(r.issues), 'W-203'))
  const bad = convertV1ToV2({ nodes: [{ type: 'start' }, { id: 'e', type: 'end', data: {} }], edges: [] })
  t('缺 id 节点 failed', bad.report.nodeDiffs.some((d) => d.status === 'failed'))
}

// ============ 8. 报告完整性 ============
{
  const r = convertV1ToV2(FIXTURE_FULL_FLOW)
  t('summary 计数守恒',
    r.report.summary.total === 6 &&
    r.report.summary.total === r.report.summary.converted + r.report.summary.degraded + r.report.summary.failed)
  t('meta.converted_from=v1', r.graph.meta.converted_from === 'v1')
  t('meta.conversion 摘要', r.graph.meta.conversion.converted === r.report.summary.converted)
}

// ============ 9. 分支映射与位置保留 ============
{
  const g = {
    nodes: [
      { id: 's', type: 'start', data: {}, position: { x: 1, y: 2 } },
      { id: 'c', type: 'condition', data: { condition: 'x>1' }, position: { x: 300, y: 2 } },
      { id: 'l1', type: 'llm', data: { prompt: 'a', model_id: 'm' }, position: { x: 600, y: 0 } },
      { id: 'l2', type: 'llm', data: { prompt: 'b', model_id: 'm' }, position: { x: 600, y: 100 } },
      { id: 'e', type: 'end', data: {}, position: { x: 900, y: 50 } }
    ],
    edges: [
      { source: 's', target: 'c' },
      { source: 'c', target: 'l1', condition: 'x>1' },
      { source: 'c', target: 'l2' },
      { source: 'l1', target: 'e' },
      { source: 'l2', target: 'e' }
    ]
  }
  const r = convertV1ToV2(g)
  const eTrue = r.graph.edges.find((e) => e.source === 'c' && e.target === 'l1')
  const eFalse = r.graph.edges.find((e) => e.source === 'c' && e.target === 'l2')
  t('condition 带表达式→true 分支', eTrue?.sourceHandle === 'true' && eTrue?.condition === 'x>1')
  t('condition 无表达式→false 分支', eFalse?.sourceHandle === 'false')
  t('分支判定记 W-203 人工核对', r.issues.filter((i) => i.code === 'W-203').length >= 2)
  t('有 position 不重建（无 W-204）', !r.issues.some((i) => i.code === 'W-204'))
  t('position 原样保留', r.graph.nodes.find((n) => n.id === 's')?.position?.x === 1)
}

// ============ 10. 性能冒烟（PRD：单工作流 ≤200 节点）============
{
  const nodes = [{ id: 's', type: 'start', data: {} }]
  const edges = []
  let prev = 's'
  for (let i = 0; i < 198; i += 1) {
    const id = `l${i}`
    nodes.push({ id, type: 'llm', data: { prompt: 'x', model_id: 'm' } })
    edges.push({ source: prev, target: id })
    prev = id
  }
  nodes.push({ id: 'e', type: 'end', data: {} })
  edges.push({ source: prev, target: 'e' })
  const t0 = Date.now()
  const r = convertV1ToV2({ nodes, edges })
  const cost = Date.now() - t0
  t('200 节点转换成功', r.graph.nodes.length === 200 && r.report.summary.converted === 200)
  t('200 节点转换 < 2000ms', cost < 2000)
  t('200 节点产物 0 error', errors(r.issues).length === 0)
}

console.log(`\nconverter.test: ${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)
