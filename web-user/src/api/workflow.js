/**
 * 用户侧工作流 API（T8）
 * 路径溯源：T7 节点1 裁定 Q1 落地映射 —— /v1/agent/u/workflows/*
 * 错误约定：40901 乐观锁冲突（带 current_draft_version）；42200 校验阻断（带 issues）；
 * 40401 归属不命中按不存在处理（M8，不暴露存在性）。
 */
import request from '@/utils/request'

/** 我的工作流列表（M8 仅返回 own/linked） */
export function getMyWorkflows(params) {
  return request({ url: '/v1/agent/u/workflows', method: 'get', params })
}

/**
 * 新建工作流
 * @param {{name:string, description?:string, icon?:string, template_id?:number}} data
 * graph_json 缺省时后端自动生成 start→end 骨架
 */
export function createWorkflow(data) {
  return request({ url: '/v1/agent/u/workflows', method: 'post', data })
}

/** 工作流详情（返回含 definition(Schema v2 草稿) + validation 摘要） */
export function getWorkflowDetail(id) {
  return request({ url: `/v1/agent/u/workflows/${id}`, method: 'get' })
}

/**
 * 保存草稿（乐观锁）
 * @param {number} id
 * @param {{graph_json:Object, draft_version:number, client_trace_id?:string}} data
 */
export function saveDraft(id, data) {
  return request({ url: `/v1/agent/u/workflows/${id}/draft`, method: 'put', data })
}

/** 服务端全量校验（含 E-108/E-110 等 server-only 项） */
export function validateWorkflow(id, graphJson) {
  return request({ url: `/v1/agent/u/workflows/${id}/validate`, method: 'post', data: { graph_json: graphJson } })
}

/** 删除工作流（草稿与发布版一并删除，M8 归属校验） */
export function deleteWorkflow(id) {
  return request({ url: `/v1/agent/u/workflows/${id}`, method: 'delete' })
}

// ============================================================
// T13 发布管理
// ============================================================

/**
 * 发布工作流（04-F1）
 * 幂等键 24h 去重（重放返回原响应）→ 全量校验（错误阻断 422）→ 生成不可变版本
 * @param {number} id @param {string} idempotencyKey 前端生成 UUID，同次重试复用同键
 * @returns Promise<{version_id:number, version_no:number, published_at:string}>
 */
export function publishWorkflow(id, idempotencyKey) {
  return request({
    url: `/v1/agent/u/workflows/${id}/publish`,
    method: 'post',
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}
  })
}

/** 版本列表（按 version_no 倒序，只读） @returns Promise<VersionInfo[]> */
export function listVersions(id) {
  return request({ url: `/v1/agent/u/workflows/${id}/versions`, method: 'get' })
}

/** 版本快照（只读，含 graph_json 用于只读预览） */
export function getVersionSnapshot(id, versionNo) {
  return request({ url: `/v1/agent/u/workflows/${id}/versions/${versionNo}`, method: 'get' })
}

/**
 * 回滚：以旧版本 graph_json 生成新发布版本（旧版本不可变；不改草稿）
 * 新图过全量校验，失效资源 E-108/E-110 阻断（422）
 * @returns Promise<{version_no:number, ...}> 新版本号
 */
export function rollbackWorkflow(id, versionNo) {
  return request({ url: `/v1/agent/u/workflows/${id}/rollback`, method: 'post', data: { version_no: versionNo } })
}

/** 停用已发布工作流 @returns Promise<{status:string, draft_version:number}> */
export function disableWorkflow(id) {
  return request({ url: `/v1/agent/u/workflows/${id}/disable`, method: 'post' })
}
