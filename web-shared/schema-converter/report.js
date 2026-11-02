/**
 * 转换报告与降级 issue 组装（T9）
 * W-2xx 码段（warning 级，与 E-1xx 校验码区分）：
 * W-201 不支持节点降级 / W-202 字段无对应丢弃 / W-203 边语义降级 / W-204 位置信息重建
 */
export const W_CODES = {
  W201: 'W-201',
  W202: 'W-202',
  W203: 'W-203',
  W204: 'W-204'
}

/** 转换器降级 issue（结构对齐 validator issue，level 固定 warning） */
export function makeWarn(code, message, extra = {}) {
  const item = { code, level: 'warning', message }
  if (extra.nodeId != null) item.node_id = extra.nodeId
  if (extra.edgeId != null) item.edge_id = extra.edgeId
  if (extra.field != null) item.field = extra.field
  return item
}

/** 创建空报告 */
export function createReport() {
  return {
    summary: { total: 0, converted: 0, degraded: 0, failed: 0 },
    nodeDiffs: [],
    edgeDiffs: []
  }
}

export function addNodeDiff(report, diff) {
  report.nodeDiffs.push(diff)
  report.summary.total += 1
  if (diff.status === 'converted') report.summary.converted += 1
  else if (diff.status === 'degraded') report.summary.degraded += 1
  else report.summary.failed += 1
}

export function addEdgeDiff(report, diff) {
  report.edgeDiffs.push(diff)
}
