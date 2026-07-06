import request from '@/utils/request'

// ==================== 流程配置 ====================

export const getFlowList = (params) => {
  return request.get('/v1/approval/flows', { params })
}

export const getFlowDetail = (id) => {
  return request.get(`/v1/approval/flows/${id}`)
}

export const createFlow = (data) => {
  return request.post('/v1/approval/flows', data)
}

export const updateFlow = (id, data) => {
  return request.put(`/v1/approval/flows/${id}`, data)
}

export const deleteFlow = (id) => {
  return request.delete(`/v1/approval/flows/${id}`)
}

export const toggleFlowStatus = (id, isActive) => {
  return request.post(`/v1/approval/flows/${id}/toggle`, { is_active: isActive })
}

export const getFlowByBusinessType = (businessType) => {
  return request.get(`/v1/approval/flows/business-type/${businessType}`)
}

// ==================== 审批实例 ====================

export const createInstance = (data) => {
  return request.post('/v1/approval/instances', data)
}

export const getInstanceList = (params) => {
  return request.get('/v1/approval/instances', { params })
}

export const getInstanceDetail = (id) => {
  return request.get(`/v1/approval/instances/${id}`)
}

export const cancelInstance = (id) => {
  return request.post(`/v1/approval/instances/${id}/cancel`)
}

export const getInstanceByBusiness = (businessType, businessId) => {
  return request.get(`/v1/approval/instances/business/${businessType}/${businessId}`)
}

// ==================== 审批任务 ====================

export const getMyTasks = (params) => {
  return request.get('/v1/approval/tasks/my', { params })
}

export const getTaskDetail = (id) => {
  return request.get(`/v1/approval/tasks/${id}`)
}

export const approveTask = (id, data) => {
  return request.post(`/v1/approval/tasks/${id}/approve`, data)
}

export const transferTask = (id, data) => {
  return request.post(`/v1/approval/tasks/${id}/transfer`, data)
}

// ==================== 审批规则 ====================

export const getRuleList = (params) => {
  return request.get('/v1/approval/rules', { params })
}

export const getRuleDetail = (id) => {
  return request.get(`/v1/approval/rules/${id}`)
}

export const createRule = (data) => {
  return request.post('/v1/approval/rules', data)
}

export const updateRule = (id, data) => {
  return request.put(`/v1/approval/rules/${id}`, data)
}

export const deleteRule = (id) => {
  return request.delete(`/v1/approval/rules/${id}`)
}

export const toggleRuleStatus = (id, isActive) => {
  return request.post(`/v1/approval/rules/${id}/toggle`, null, { params: { is_active: isActive } })
}

export const checkApprovalRequired = (path, method) => {
  return request.post('/v1/approval/rules/check', null, { params: { path, method } })
}
