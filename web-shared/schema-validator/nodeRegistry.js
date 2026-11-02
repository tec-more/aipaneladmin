/**
 * 用户域节点注册表（单一事实源）
 * 溯源：graph_validator.py L48-L60（域开关）、L303-L320（必填输入）；
 * PRD §5 各节点出入参、§5.11 开放矩阵；T8 节点1 裁定 Q1（6 类 open，其余置灰）。
 * 画布渲染、连线校验、全量校验三处共同消费，禁止在别处重复定义端口。
 */

/** 用户域永久禁用（R-10 code；PRD §5.11 vector P0 不开放） */
export const FORBIDDEN_TYPES = new Set(['code', 'vector'])

/**
 * @typedef {Object} NodeMeta
 * @property {string} type @property {string} label @property {string} category
 * @property {string} icon
 * @property {'open'|'gray'|'disabled'} availability
 * @property {string} [disabledReason]
 * @property {Object} defaultConfig
 * @property {Array<{name:string, type:string, required?:boolean}>} inputs
 * @property {Array<{name:string, type:string}>} outputs
 */
export const NODE_REGISTRY = {
  start: {
    type: 'start', label: '开始', category: '基础', icon: 'VideoPlay',
    availability: 'open',
    defaultConfig: { entry_mode: 'chat' },
    inputs: [],
    outputs: [
      { name: 'user_input', type: 'string' },
      { name: 'attachments', type: 'array<file>' },
      { name: 'session_id', type: 'string' },
      { name: 'user_profile', type: 'object' }
    ]
  },
  end: {
    type: 'end', label: '结束', category: '基础', icon: 'CircleCheck',
    availability: 'open',
    defaultConfig: { output_mode: 'last' },
    inputs: [{ name: 'answer', type: 'any' }],
    outputs: []
  },
  llm: {
    type: 'llm', label: 'LLM 对话', category: 'AI 能力', icon: 'ChatDotRound',
    availability: 'open',
    // 端口以 PRD §5.2 为权威（T10 节点1 裁定 Q1：静态端口，不建动态端口引擎）；
    // query 为用户问题直连接口（start.user_input 数据流必需，对应架构 04 §3 示例的 question 端口）
    inputs: [
      { name: 'query', type: 'string' },
      { name: 'prompt_vars', type: 'object' },
      { name: 'context', type: 'chunk[]' },
      { name: 'history', type: 'message[]' }
    ],
    outputs: [
      { name: 'text', type: 'string' },
      { name: 'structured', type: 'object' },
      { name: 'usage', type: 'object' },
      { name: 'raw', type: 'object' }
    ],
    defaultConfig: {
      model_ref: '', system_prompt: '', user_prompt: '',
      history_mode: 'last_n', history_turns: 6,
      temperature: 0.3, max_output_tokens: null,
      output_mode: 'text', output_schema: null,
      stream: true, stop: [], citation_required: false, fallback_model_ref: ''
    },
    // 表单 Schema（required 与 E-100 服务端权威对齐；默认值与 PRD 逐字段一致）
    fields: [
      { key: 'model_ref', label: '模型', type: 'string', required: true, widget: 'resource_ref', resourceKind: 'model', help: '必须属于授权清单，否则保存时 E-110' },
      { key: 'user_prompt', label: '用户提示词', type: 'text', required: true, widget: 'textarea', help: '支持 {{变量}} 插值；必须至少引用一个输入或常量' },
      { key: 'system_prompt', label: '系统提示词', type: 'text', widget: 'textarea', help: '支持变量插值；≤ 8000 字符' },
      { key: 'history_mode', label: '历史模式', type: 'enum', required: true, default: 'last_n', options: [{ value: 'none', label: '不携带' }, { value: 'last_n', label: '最近 N 轮' }, { value: 'summary', label: '摘要' }] },
      { key: 'history_turns', label: '历史轮数', type: 'integer', default: 6, min: 1, max: 50, help: '受上下文预算二次裁剪' },
      { key: 'temperature', label: '温度', type: 'number', default: 0.3, min: 0, max: 2, step: 0.1, help: '结构化输出建议 ≤ 0.5' },
      { key: 'max_output_tokens', label: '最大输出 Token', type: 'integer', min: 1, help: '不得超过套餐上限；留空按模型上限' },
      { key: 'output_mode', label: '输出模式', type: 'enum', required: true, default: 'text', options: [{ value: 'text', label: '文本' }, { value: 'json_object', label: 'JSON 对象' }, { value: 'json_schema', label: 'JSON Schema' }] },
      { key: 'output_schema', label: '输出 Schema', type: 'object', widget: 'json', help: 'output_mode 为 json_schema 时必填' },
      { key: 'stream', label: '流式输出', type: 'boolean', default: true },
      { key: 'stop', label: '停止词', type: 'array<string>', widget: 'json', help: '≤ 4 条' },
      { key: 'citation_required', label: '引用必填', type: 'boolean', default: false, help: '开启后无引用时标记「未溯源」' },
      { key: 'fallback_model_ref', label: '备用模型', type: 'string', widget: 'resource_ref', resourceKind: 'model', help: '主模型失败时切换，须已授权' }
    ]
  },
  rag_retrieval: {
    type: 'rag_retrieval', label: '知识检索', category: 'AI 能力', icon: 'Collection',
    availability: 'open',
    // 端口与配置字段以 PRD §5.3 为权威
    inputs: [
      { name: 'query', type: 'string', required: true },
      { name: 'filters', type: 'object' }
    ],
    outputs: [
      { name: 'chunks', type: 'chunk[]' },
      { name: 'citations', type: 'array<object>' },
      { name: 'empty', type: 'boolean' },
      { name: 'stats', type: 'object' }
    ],
    defaultConfig: {
      knowledge_base_refs: [], top_k: 8, score_threshold: 0.2,
      rerank_enabled: true, rerank_top_n: 4,
      query_rewrite: 'off', metadata_filter_mode: 'merge',
      citation_required: true, empty_strategy: 'return_empty', max_context_tokens: 2000
    },
    fields: [
      { key: 'knowledge_base_refs', label: '知识库', type: 'array<string>', required: true, widget: 'resource_ref', resourceKind: 'kb', help: '≥1；必须在授权范围内' },
      { key: 'top_k', label: '召回条数 top_k', type: 'integer', required: true, default: 8, min: 1, max: 50, help: '受套餐上限约束' },
      { key: 'score_threshold', label: '分数阈值', type: 'number', default: 0.2, min: 0, max: 1, step: 0.05, help: '为空则不过滤' },
      { key: 'rerank_enabled', label: '重排', type: 'boolean', required: true, default: true, help: '关闭需提示效果影响' },
      { key: 'rerank_top_n', label: '重排保留数', type: 'integer', default: 4, min: 1, help: '≤ top_k' },
      { key: 'query_rewrite', label: '查询改写', type: 'enum', required: true, default: 'off', options: [{ value: 'off', label: '关闭' }, { value: 'expand', label: '扩展' }, { value: 'hyde', label: 'HyDE' }], help: '开启计入额外 token' },
      { key: 'metadata_filter_mode', label: '过滤合并模式', type: 'enum', required: true, default: 'merge', options: [{ value: 'merge', label: '与外部 filters 合并' }, { value: 'override', label: '覆盖' }] },
      { key: 'citation_required', label: '引用必填', type: 'boolean', required: true, default: true, help: '关闭则输出不含来源' },
      { key: 'empty_strategy', label: '空召回策略', type: 'enum', required: true, default: 'return_empty', options: [{ value: 'return_empty', label: '返回空' }, { value: 'error', label: '报错' }, { value: 'fallback_message', label: '兜底文案' }] },
      { key: 'max_context_tokens', label: '上下文 Token 上限', type: 'integer', default: 2000, min: 100, help: '超限按分数截断' }
    ]
  },
  condition: {
    type: 'condition', label: '条件分支', category: '流程控制', icon: 'Switch',
    availability: 'open',
    defaultConfig: { expression: '' },
    inputs: [{ name: 'input', type: 'any', required: true }],
    outputs: [
      { name: 'true', type: 'boolean' },
      { name: 'false', type: 'boolean' }
    ],
    fields: [
      { key: 'expression', label: '条件表达式', type: 'text', required: true, widget: 'textarea', help: '如 {{节点.端口}} > 10；表达式求值由引擎执行，前端仅透传' }
    ]
  },
  loop: {
    type: 'loop', label: '循环', category: '流程控制', icon: 'RefreshRight',
    availability: 'open',
    defaultConfig: { mode: 'array', max_iterations: 10, exit_condition: '' },
    inputs: [
      { name: 'items', type: 'array<any>' },
      { name: 'body_in', type: 'any', required: true }
    ],
    outputs: [{ name: 'results', type: 'array<any>' }],
    fields: [
      { key: 'mode', label: '循环模式', type: 'enum', required: true, default: 'array', options: [{ value: 'count', label: '计数' }, { value: 'array', label: '数组遍历' }, { value: 'while', label: '条件循环' }] },
      { key: 'max_iterations', label: '最大迭代次数', type: 'integer', required: true, default: 10, min: 1, max: 100, help: '套餐权威上限由服务端裁定' },
      { key: 'exit_condition', label: '退出条件', type: 'string', required: true, help: '必填；如 {{loop.index}} >= 5' }
    ]
  },
  sub_workflow: {
    type: 'sub_workflow', label: '子工作流', category: '流程控制', icon: 'Share',
    availability: 'open',
    defaultConfig: { workflow_ref: null, version: 'latest', param_mapping: {}, result_mapping: {} },
    inputs: [{ name: 'inputs', type: 'object', required: true }],
    outputs: [{ name: 'outputs', type: 'object' }],
    fields: [
      { key: 'workflow_ref', label: '子工作流引用', type: 'string', required: true, widget: 'resource_ref', resourceKind: 'workflow', help: '须为已发布且可见的工作流' },
      { key: 'version', label: '版本', type: 'string', default: 'latest', help: 'latest 或指定版本号' },
      { key: 'param_mapping', label: '入参映射', type: 'object', widget: 'json', help: '逐字段映射，缺必填参数保存阻断' },
      { key: 'result_mapping', label: '结果映射', type: 'object', widget: 'json' }
    ]
  },
  template: {
    type: 'template', label: '模板渲染', category: 'AI 能力', icon: 'Tickets',
    availability: 'open',
    defaultConfig: { template: '' },
    inputs: [{ name: 'input', type: 'any' }],
    outputs: [{ name: 'output', type: 'string' }],
    fields: [
      { key: 'template', label: '模板内容', type: 'text', required: true, widget: 'textarea', help: '支持 {{变量}} 插值' }
    ]
  },
  hitl: {
    type: 'hitl', label: '人工卡点', category: '流程控制', icon: 'User',
    availability: 'gray', disabledReason: '受限节点：待授权开放（T11）',
    defaultConfig: { assignee: null, timeout_action: 'fail' },
    inputs: [{ name: 'context', type: 'object', required: true }],
    outputs: [{ name: 'approved', type: 'boolean' }, { name: 'comment', type: 'string' }]
  },
  sub_agent: {
    type: 'sub_agent', label: '子 Agent', category: 'AI 能力', icon: 'Monitor',
    availability: 'gray', disabledReason: '受限节点：视套餐开放（T11）',
    defaultConfig: { agent_ref: null },
    inputs: [{ name: 'task', type: 'string', required: true }],
    outputs: [{ name: 'result', type: 'string' }]
  },
  tool: {
    type: 'tool', label: '工具调用', category: 'AI 能力', icon: 'Wrench',
    availability: 'gray', disabledReason: '白名单节点：仅授权工具（T11）',
    defaultConfig: { tool_ref: null },
    inputs: [{ name: 'params', type: 'object', required: true }],
    outputs: [{ name: 'result', type: 'any' }]
  },
  http: {
    type: 'http', label: 'HTTP 请求', category: '集成', icon: 'Link',
    availability: 'disabled', disabledReason: 'P0 不开放：需域名白名单（R-10）',
    defaultConfig: { url: '', method: 'GET' },
    inputs: [],
    outputs: [{ name: 'response', type: 'object' }]
  },
  vector: {
    type: 'vector', label: '向量库', category: '集成', icon: 'Coin',
    availability: 'disabled', disabledReason: 'P0 不开放：高级节点（P1）',
    defaultConfig: {},
    inputs: [],
    outputs: []
  },
  code: {
    type: 'code', label: '代码执行', category: '集成', icon: 'Document',
    availability: 'disabled', disabledReason: '用户域永久关闭（R-10）',
    defaultConfig: {},
    inputs: [],
    outputs: []
  }
}

/** 节点库分组顺序（C1） */
export const NODE_CATEGORIES = ['基础', 'AI 能力', '流程控制', '集成']

/** 节点类型别名归一（与服务端 _TYPE_ALIASES 一致） */
export const TYPE_ALIASES = { trigger: 'start', rag: 'rag_retrieval', tool_call: 'tool' }

/**
 * 归一节点类型
 * @param {string} t
 * @returns {string}
 */
export function normalizeNodeType(t) {
  return TYPE_ALIASES[t] || t
}

/**
 * 取节点元数据（归一后）；未知类型返回 null
 * @param {string} type
 * @returns {NodeMeta|null}
 */
export function getNodeMeta(type) {
  return NODE_REGISTRY[normalizeNodeType(type)] || null
}

/**
 * 解析节点端口类型：优先节点 data 内声明，兜底注册表默认
 * @param {Object} node Schema v2 节点
 * @param {'inputs'|'outputs'} direction
 * @param {string} portName
 * @returns {string|null} 端口类型；端口不存在返回 null
 */
export function resolvePortType(node, direction, portName) {
  const declared = node?.data?.[direction]
  if (Array.isArray(declared)) {
    const hit = declared.find((p) => p && p.name === portName)
    if (hit) return hit.type || 'any'
  }
  const meta = getNodeMeta(node?.type)
  const fallback = meta?.[direction]?.find((p) => p.name === portName)
  return fallback ? fallback.type : null
}
