/**
 * v1 图样例集（R-B 样本覆盖）
 * 主样例移植自后端 base/plugins/agent/tests/test_node_types.py L1276-L1292（工作流9完整流程）。
 */

/** 后端 fixture 原样移植：变量赋值→迭代→条件→输出 */
export const FIXTURE_FULL_FLOW = {
  nodes: [
    { id: 'start-1', type: 'start', data: { label: '开始' } },
    { id: 'va-1', type: 'variable_assigner', data: { label: '变量赋值', variable_name: 'items', value: '["apple","banana","orange"]' } },
    { id: 'it-1', type: 'iteration', data: { label: '迭代', iterationList: 'items', iterationVariable: 'item' } },
    { id: 'cond-1', type: 'condition', data: { label: '条件判断', condition: '{{iteration_index}} < {{iteration_total}}' } },
    { id: 'out-1', type: 'output', data: { label: '输出', outputContent: '{{item}}' } },
    { id: 'end-1', type: 'end', data: { label: '结束' } }
  ],
  edges: [
    { source: 'start-1', target: 'va-1' },
    { source: 'va-1', target: 'it-1' },
    { source: 'it-1', target: 'cond-1' },
    { source: 'cond-1', target: 'out-1', condition: '{{iteration_index}} < {{iteration_total}}' },
    { source: 'out-1', target: 'end-1' }
  ]
}

/** 全 converted 图（llm + template + condition + loop）：产物应 0 error（除 loop 退出条件 E-111） */
export const FIXTURE_CONVERTIBLE = {
  nodes: [
    { id: 's', type: 'start', data: { label: '开始' } },
    { id: 'l1', type: 'llm', data: { label: '问答', prompt: '回答：{{s.user_input}}', model_id: 'gpt-4o', temperature: 0.5, max_tokens: 1024, outputVar: 'ans', skill_ids: [1] } },
    { id: 't1', type: 'template', data: { label: '渲染', template: '结果：{{l1.answer}}', outputVar: 'text' } },
    { id: 'e', type: 'end', data: { label: '结束' } }
  ],
  edges: [
    { source: 's', target: 'l1' },
    { source: 'l1', target: 't1' },
    { source: 't1', target: 'e' }
  ]
}

/** 降级类型集合：http/code/skill/parallel/aggregate/document_extract */
export const FIXTURE_DEGRADED = {
  nodes: [
    { id: 's', type: 'start', data: { label: '开始' } },
    { id: 'h1', type: 'http', data: { label: '调接口', url: 'https://a.b/c', method: 'GET' } },
    { id: 'c1', type: 'code', data: { label: '跑代码', code: 'return 1' } },
    { id: 'k1', type: 'skill', data: { label: '技能', skill_id: 'sk1' } },
    { id: 'p1', type: 'parallel', data: { label: '并行' } },
    { id: 'a1', type: 'aggregate', data: { label: '聚合', input_vars: ['a', 'b'] } },
    { id: 'd1', type: 'document_extract', data: { label: '提取', document_var: 'doc' } },
    { id: 'e', type: 'end', data: { label: '结束' } }
  ],
  edges: [
    { source: 's', target: 'h1' },
    { source: 'h1', target: 'c1' },
    { source: 'c1', target: 'e' }
  ]
}

/** v1 计数 loop */
export const FIXTURE_COUNT_LOOP = {
  nodes: [
    { id: 's', type: 'start', data: { label: '开始' } },
    { id: 'lp', type: 'loop', data: { label: '循环', loop_count: 5, loop_var: 'i' } },
    { id: 'e', type: 'end', data: { label: '结束' } }
  ],
  edges: [
    { source: 's', target: 'lp' },
    { source: 'lp', target: 'e' }
  ]
}

/** 边界：未知节点类型 */
export const FIXTURE_UNKNOWN_TYPE = {
  nodes: [
    { id: 's', type: 'start', data: { label: '开始' } },
    { id: 'x1', type: 'quantum_node', data: { label: '未知', foo: 1 } },
    { id: 'e', type: 'end', data: { label: '结束' } }
  ],
  edges: [{ source: 's', target: 'x1' }, { source: 'x1', target: 'e' }]
}
