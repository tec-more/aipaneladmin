/**
 * 校验错误码常量与默认文案（PRD §4.5 权威来源；与服务端 graph_validator.py 对齐）
 * level：error=阻断保存/发布；warning=提示（E-106）
 */
export const LEVEL_ERROR = 'error'
export const LEVEL_WARNING = 'warning'

export const CODES = {
  E100: { code: 'E-100', level: LEVEL_ERROR, text: '节点必填配置缺失或非法' },
  E101: { code: 'E-101', level: LEVEL_ERROR, text: '端口类型不兼容' },
  E102: { code: 'E-102', level: LEVEL_ERROR, text: '必填输入未连接' },
  E103: { code: 'E-103', level: LEVEL_ERROR, text: '存在环或自连' },
  E104: { code: 'E-104', level: LEVEL_ERROR, text: '重复连线' },
  E105: { code: 'E-105', level: LEVEL_ERROR, text: '输入端已被占用' },
  E106: { code: 'E-106', level: LEVEL_WARNING, text: '输出端口悬空' },
  E107: { code: 'E-107', level: LEVEL_ERROR, text: '引用了未声明的变量' },
  E108: { code: 'E-108', level: LEVEL_ERROR, text: '子工作流版本失效（服务端校验）' },
  E109: { code: 'E-109', level: LEVEL_ERROR, text: '使用了未授权节点类型' },
  E110: { code: 'E-110', level: LEVEL_ERROR, text: '使用了未授权资源（服务端校验）' },
  E111: { code: 'E-111', level: LEVEL_ERROR, text: '循环缺少退出条件或超出上限' },
  E112: { code: 'E-112', level: LEVEL_ERROR, text: 'HITL 未配置审批人或超时策略' },
  E113: { code: 'E-113', level: LEVEL_WARNING, text: '节点与开始节点不连通（本地检查）' }
}

/**
 * 构造校验 issue（结构与服务端 _issue() 完全同构）
 * @param {string} code E-1xx
 * @param {string} message 具体文案
 * @param {{nodeId?:string, edgeId?:string, level?:string, field?:string}} [extra]
 * @returns {import('../index.js').ValidationIssue}
 */
export function makeIssue(code, message, extra = {}) {
  const meta = CODES[code.replace('-', '')] || { level: LEVEL_ERROR }
  const item = { code, level: extra.level || meta.level, message }
  if (extra.nodeId != null) item.node_id = extra.nodeId
  if (extra.edgeId != null) item.edge_id = extra.edgeId
  if (extra.field != null) item.field = extra.field
  return item
}
