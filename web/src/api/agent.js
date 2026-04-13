import request from '@/utils/request'

// ==================== 智能体管理 ====================

export function getAgents(params) {
  return request.get('/v1/agent/agents/', { params })
}

export function getAgent(id) {
  return request.get(`/v1/agent/agents/${id}`)
}

export function createAgent(data) {
  return request.post('/v1/agent/agents/', data)
}

export function updateAgent(id, data) {
  return request.put(`/v1/agent/agents/${id}`, data)
}

export function deleteAgent(id) {
  return request.delete(`/v1/agent/agents/${id}`)
}

export function getAgentSkills(agentId) {
  return request.get(`/v1/agent/agents/${agentId}/skills`)
}

export function addSkillToAgent(agentId, skillId) {
  return request.post(`/v1/agent/agents/${agentId}/skills/${skillId}`)
}

export function removeSkillFromAgent(agentId, skillId) {
  return request.delete(`/v1/agent/agents/${agentId}/skills/${skillId}`)
}

export function setAgentSkills(agentId, skillIds) {
  return request.put(`/v1/agent/agents/${agentId}/skills`, { skill_ids: skillIds })
}

// ==================== 技能管理 ====================

export function getSkills(params) {
  return request.get('/v1/agent/skills/', { params })
}

export function getSkill(id) {
  return request.get(`/v1/agent/skills/${id}`)
}

export function createSkill(data) {
  return request.post('/v1/agent/skills/', data)
}

export function updateSkill(id, data) {
  return request.put(`/v1/agent/skills/${id}`, data)
}

export function deleteSkill(id) {
  return request.delete(`/v1/agent/skills/${id}`)
}

export function getSkillsByType(skillType) {
  return request.get(`/v1/agent/skills/type/${skillType}`)
}

export function getActiveSkills() {
  return request.get('/v1/agent/skills/active/list')
}

export function executeSkill(id, params) {
  return request.post(`/v1/agent/skills/${id}/execute`, params)
}

export function getSkillUsage(id) {
  return request.get(`/v1/agent/skills/${id}/usage`)
}

// ==================== 记忆管理 ====================

export function getMemories(params) {
  return request.get('/v1/agent/memories/', { params })
}

export function getMemory(id) {
  return request.get(`/v1/agent/memories/${id}`)
}

export function createMemory(data) {
  return request.post('/v1/agent/memories/', data)
}

export function updateMemory(id, data) {
  return request.put(`/v1/agent/memories/${id}`, data)
}

export function deleteMemory(id) {
  return request.delete(`/v1/agent/memories/${id}`)
}

export function getMemoriesByAgent(agentId) {
  return request.get(`/v1/agent/memories/agent/${agentId}`)
}

export function getMemoriesByAgentAndType(agentId, memoryType) {
  return request.get(`/v1/agent/memories/agent/${agentId}/type/${memoryType}`)
}

export function recallMemory(id, params) {
  return request.post(`/v1/agent/memories/${id}/recall`, params)
}

export function getRecentMemories(agentId) {
  return request.get(`/v1/agent/memories/agent/${agentId}/recent`)
}

export function getImportantMemories(agentId) {
  return request.get(`/v1/agent/memories/agent/${agentId}/important`)
}

export function searchMemories(agentId, params) {
  return request.get(`/v1/agent/memories/agent/${agentId}/search`, { params })
}

export function getMemoryStats(agentId) {
  return request.get(`/v1/agent/memories/agent/${agentId}/stats`)
}

// ==================== 工作流管理 ====================

export function getWorkflows(params) {
  return request.get('/v1/agent/workflows/', { params })
}

export function getWorkflow(id) {
  return request.get(`/v1/agent/workflows/${id}`)
}

export function createWorkflow(data) {
  return request.post('/v1/agent/workflows/', data)
}

export function updateWorkflow(id, data) {
  return request.put(`/v1/agent/workflows/${id}`, data)
}

export function deleteWorkflow(id) {
  return request.delete(`/v1/agent/workflows/${id}`)
}

export function createWorkflowNode(workflowId, data) {
  return request.post(`/v1/agent/workflows/${workflowId}/nodes`, data)
}

export function createWorkflowEdge(workflowId, data) {
  return request.post(`/v1/agent/workflows/${workflowId}/edges`, data)
}

export function executeWorkflow(id, params) {
  return request.post(`/v1/agent/workflows/${id}/execute`, params)
}

export function getWorkflowExecutions(params) {
  return request.get('/v1/agent/workflow-executions', { params })
}

export function getWorkflowExecution(id) {
  return request.get(`/v1/agent/workflow-executions/${id}`)
}

// ==================== 对话流管理 ====================

export function getDialogFlows(params) {
  return request.get('/v1/agent/dialog-flows', { params })
}

export function getDialogFlow(id) {
  return request.get(`/v1/agent/dialog-flows/${id}`)
}

export function createDialogFlow(data) {
  return request.post('/v1/agent/dialog-flows', data)
}

export function updateDialogFlow(id, data) {
  return request.put(`/v1/agent/dialog-flows/${id}`, data)
}

export function deleteDialogFlow(id) {
  return request.delete(`/v1/agent/dialog-flows/${id}`)
}

export function getDialogFlowNodes(dialogFlowId) {
  return request.get(`/v1/agent/dialog-flows/${dialogFlowId}/nodes`)
}

export function createDialogFlowNode(dialogFlowId, data) {
  return request.post(`/v1/agent/dialog-flows/${dialogFlowId}/nodes`, data)
}

export function getDialogFlowNode(nodeId) {
  return request.get(`/v1/agent/dialog-flow-nodes/${nodeId}`)
}

export function updateDialogFlowNode(nodeId, data) {
  return request.put(`/v1/agent/dialog-flow-nodes/${nodeId}`, data)
}

export function deleteDialogFlowNode(nodeId) {
  return request.delete(`/v1/agent/dialog-flow-nodes/${nodeId}`)
}

export function getDialogFlowEdges(dialogFlowId) {
  return request.get(`/v1/agent/dialog-flows/${dialogFlowId}/edges`)
}

export function createDialogFlowEdge(dialogFlowId, data) {
  return request.post(`/v1/agent/dialog-flows/${dialogFlowId}/edges`, data)
}

export function getDialogFlowEdge(edgeId) {
  return request.get(`/v1/agent/dialog-flow-edges/${edgeId}`)
}

export function updateDialogFlowEdge(edgeId, data) {
  return request.put(`/v1/agent/dialog-flow-edges/${edgeId}`, data)
}

export function deleteDialogFlowEdge(edgeId) {
  return request.delete(`/v1/agent/dialog-flow-edges/${edgeId}`)
}

export function executeDialogFlow(id, params) {
  return request.post(`/v1/agent/dialog-flows/${id}/execute`, params)
}

export function getDialogFlowExecution(executionId) {
  return request.get(`/v1/agent/dialog-flow-executions/${executionId}`)
}

export function getDialogFlowExecutions(params) {
  return request.get('/v1/agent/dialog-flow-executions', { params })
}
