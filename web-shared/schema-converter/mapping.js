/**
 * v1→v2 节点映射表（单一事实源，T9 节点1 裁定 Q3/Q5 冻结）
 * v1 源：Agent.graph_definition（langgraph_executor 消费的节点类型与字段）。
 * 规则：converted=语义直映；degraded=保留原类型生成节点 + W-201，原文入 report，不静默丢弃。
 * droppedFields：v1 有而 v2 无对应语义的字段，记入 report（W-202），不写入 v2 config。
 */

/** 端口映射：v1 控制流边无端口语义，按目标/源节点给默认 handle */
export const DEFAULT_TARGET_HANDLE = {
  condition: 'input',
  loop: 'body_in',
  sub_workflow: 'inputs',
  end: 'answer',
  llm: 'query',
  rag_retrieval: 'query',
  template: 'input'
}

export const DEFAULT_SOURCE_HANDLE = {
  start: 'user_input',
  llm: 'text',
  rag_retrieval: 'chunks',
  template: 'output',
  sub_workflow: 'outputs'
}

/**
 * @typedef {Object} MappingRule
 * @property {string|null} v2Type        // null=degraded 保留 v1 原类型
 * @property {(d:Object)=>({config:Object, dropped:string[]})} [mapConfig]
 */
export const V1_NODE_MAPPING = {
  start: {
    v2Type: 'start',
    mapConfig: () => ({ config: {}, dropped: [] })
  },
  end: {
    v2Type: 'end',
    mapConfig: () => ({ config: {}, dropped: [] })
  },
  llm: {
    v2Type: 'llm',
    mapConfig: (d) => ({
      config: {
        model_ref: d.model_id ?? d.modelId ?? '',
        user_prompt: d.prompt ?? '',
        system_prompt: d.system_prompt ?? '',
        temperature: d.temperature ?? 0.3,
        max_tokens: d.max_tokens ?? 2048,
        history_mode: 'none'
      },
      // v2 llm 输出固定 answer；技能绑定属工具域（T11），均降级记录
      dropped: ['outputVar', 'skill_ids', 'skillIds', 'stream'].filter((k) => d[k] != null)
    })
  },
  template: {
    v2Type: 'template',
    mapConfig: (d) => ({
      config: { template: d.template ?? '' },
      dropped: ['outputVar'].filter((k) => d[k] != null)
    })
  },
  condition: {
    v2Type: 'condition',
    mapConfig: (d) => ({
      config: { expression: d.condition ?? '' },
      dropped: []
    })
  },
  // Q5：iteration（数组遍历）→ loop；iterationList 为变量引用，v2 需连线表达，记 dropped
  iteration: {
    v2Type: 'loop',
    mapConfig: (d) => ({
      config: {
        mode: 'array',
        max_iterations: 10,
        exit_condition: '' // 留空由 E-111 显式提示人工补全，不语义发明
      },
      dropped: ['iterationList', 'iterationVariable'].filter((k) => d[k] != null && d[k] !== '')
    })
  },
  // v1 loop（计数循环）→ v2 loop
  loop: {
    v2Type: 'loop',
    mapConfig: (d) => ({
      config: {
        mode: 'count',
        max_iterations: typeof d.loop_count === 'number' ? d.loop_count : 3,
        exit_condition: ''
      },
      dropped: ['loop_var'].filter((k) => d[k] != null)
    })
  },
  // ---- degraded：v2 P0 无对应语义 / 用户域未开放（保留原类型，W-201）----
  variable_assigner: { v2Type: null },
  output: { v2Type: null },
  parallel: { v2Type: null },
  skill: { v2Type: null },
  http: { v2Type: null },
  code: { v2Type: null },
  aggregate: { v2Type: null },
  document_extract: { v2Type: null }
}

/**
 * condition 出边分支判定：v1 边 condition 字段为分支表达式。
 * 无法静态判定真/假分支，默认有表达式→true、无→false，并记 W-203 供人工核对。
 */
export function mapConditionBranch(edgeCondition) {
  return edgeCondition ? 'true' : 'false'
}
