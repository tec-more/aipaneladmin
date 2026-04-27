import request, { createRequestWithTimeout } from '@/utils/request'

const longRequest = createRequestWithTimeout(300000)

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

export function executeAgent(id, params) {
  return longRequest.post(`/v1/agent/agents/${id}/execute`, params)
}

export function executeAgentGraph(id, params) {
  return longRequest.post(`/v1/agent/agents/${id}/graph/execute`, params)
}

export async function executeAgentGraphSSE(id, params, callbacks = {}) {
  const { onStart, onData, onComplete, onError } = callbacks
  const abortController = new AbortController()
  
  try {
    const response = await fetch(`/api/v1/agent/agents/${id}/graph/execute/sse`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
      signal: abortController.signal,
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    
    if (onStart) {
      onStart()
    }
    
    let buffer = ''
    
    while (true) {
      if (abortController.signal.aborted) {
        break
      }
      
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      
      const lines = buffer.split('\n')
      buffer = lines.pop()
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim()
          if (dataStr) {
            try {
              const data = JSON.parse(dataStr)
              if (onData) {
                onData(data)
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', e)
            }
          }
        }
      }
    }
    
    if (!abortController.signal.aborted && onComplete) {
      onComplete()
    }
  } catch (error) {
    if (error.name !== 'AbortError' && onError) {
      onError(error)
    }
    if (error.name !== 'AbortError') {
      throw error
    }
  }
  
  return {
    abort: () => abortController.abort()
  }
}

// 根据结构图自动选择执行方式
export async function executeAgentGraphAuto(id, params, callbacks = {}, graphDefinition = null) {
  if (!graphDefinition) {
    const graphResponse = await getAgentGraph(id)
    if (graphResponse && graphResponse.data && graphResponse.data.graph_definition) {
      graphDefinition = graphResponse.data.graph_definition
    }
  }
  
  const hasStreamingNode = hasStreamingLLMNode(graphDefinition)
  
  if (hasStreamingNode) {
    return executeAgentGraphSSE(id, params, callbacks)
  } else {
    const result = await executeAgentGraph(id, params)
    return {
      abort: () => {},
      result
    }
  }
}

export function getAgentGraph(agentId) {
  return request.get(`/v1/agent/agents/${agentId}/graph`)
}

export function updateAgentGraph(agentId, graphData) {
  return request.put(`/v1/agent/agents/${agentId}/graph`, graphData)
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

export function getMemoriesByAgentAndType(agentId, memoryType) {
  return request.get(`/v1/agent/memories/agent/${agentId}/type/${memoryType}`)
}

export function recallMemory(id, params) {
  return request.post(`/v1/agent/memories/${id}/recall`, params)
}

export function getRecentMemories(agentId) {
  return request.get(`/v1/agent/memories/agent/${agentId}/recent`)
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
  return longRequest.post(`/v1/agent/workflows/${id}/execute`, params)
}

export function getWorkflowExecutions(params) {
  return request.get('/v1/agent/workflow-executions/', { params })
}

export function getWorkflowExecution(id) {
  return request.get(`/v1/agent/workflow-executions/${id}`)
}

// ==================== 对话流管理 ====================

export function getDialogFlows(params) {
  return request.get('/v1/agent/dialog-flows/', { params })
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

export function createDialogFlowNode(dialogFlowId, data) {
  return request.post(`/v1/agent/dialog-flows/${dialogFlowId}/nodes`, data)
}

export function createDialogFlowEdge(dialogFlowId, data) {
  return request.post(`/v1/agent/dialog-flows/${dialogFlowId}/edges`, data)
}

export function executeDialogFlow(id, params) {
  return longRequest.post(`/v1/agent/dialog-flows/${id}/execute`, params)
}

export function getDialogFlowExecutions(params) {
  return request.get('/v1/agent/dialog-flows/executions', { params })
}

export function getDialogFlowExecution(id) {
  return request.get(`/v1/agent/dialog-flows/executions/${id}`)
}

// ==================== 工具函数 ====================

export function hasStreamingLLMNode(graphDefinition) {
  if (!graphDefinition || !graphDefinition.nodes) {
    return false
  }
  
  return graphDefinition.nodes.some(node => {
    if (node.type === 'llm' && node.data) {
      return node.data.stream === true
    }
    return false
  })
}
