import request, { createRequestWithTimeout } from '@/utils/request'

const requestWithLongTimeout = createRequestWithTimeout(300000)

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

/**
 * 标准的SSE执行方法 - 有while循环持续接收消息
 */
export function executeAgentGraphSSE(id, params, callbacks = {}) {
  const { onStart, onData, onComplete, onError } = callbacks
  
  // 创建安全的函数包装器
  const safeOnStart = typeof onStart === 'function' ? onStart : () => {}
  const safeOnData = typeof onData === 'function' ? onData : () => {}
  const safeOnComplete = typeof onComplete === 'function' ? onComplete : () => {}
  const safeOnError = typeof onError === 'function' ? onError : () => {}
  
  const abortController = new AbortController()
  let executionId = null
  let isAborted = false

  // 立即返回 controller，确保可以立即中断
  const controller = {
    abort: () => {
      isAborted = true
      if (executionId) {
        // 调用后端取消接口
        fetch(`/api/v1/agent/executions/${executionId}/cancel`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }).catch(() => {})
      }
      abortController.abort()
    }
  }

  // 启动SSE连接（异步，不阻塞）
  queueMicrotask(async () => {
    try {
      const response = await fetch(`/api/v1/agent/agents/${id}/graph/execute/sse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
        signal: abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      // 获取流式阅读器
      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      // 回调 - 开始
      safeOnStart()

      let buffer = ''

      // 🎯 关键的while循环 - 持续接收消息！
      while (true) {
        // 检查是否已中断
        if (isAborted || abortController.signal.aborted) {
          break
        }

        // 读取下一个数据块
        const { done, value } = await reader.read()
        if (done) {
          break
        }

        // 解码并添加到缓冲区
        buffer += decoder.decode(value, { stream: true })

        // 处理数据，按行分割
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim()
            if (dataStr) {
              try {
                const data = JSON.parse(dataStr)
                // 保存 execution_id
                if (data.type === 'start' && data.execution_id) {
                  executionId = data.execution_id
                }
                // 回调 - 收到数据
                safeOnData(data)
              } catch (e) {
                // 忽略解析错误
              }
            }
          }
        }
      }

      // 回调 - 完成
      if (!isAborted && !abortController.signal.aborted) {
        safeOnComplete()
      }
    } catch (error) {
      // 回调 - 错误
      if (error.name !== 'AbortError') {
        safeOnError(error)
      }
    }
  })

  return controller
}

// 根据结构图自动选择执行方式
export function executeAgentGraphAuto(id, params, callbacks = {}, graphDefinition = null) {
  // 立即创建 controller，支持立即中断
  let realController = null
  let isAborted = false
  
  const controller = {
    abort: () => {
      isAborted = true
      if (realController) {
        realController.abort()
      }
    }
  }

  // 异步执行剩余逻辑
  queueMicrotask(async () => {
    if (isAborted) return
    
    try {
      if (!graphDefinition) {
        const graphResponse = await getAgentGraph(id)
        if (isAborted) return
        if (graphResponse && graphResponse.data && graphResponse.data.graph_definition) {
          graphDefinition = graphResponse.data.graph_definition
        }
      }

      const hasStreamingNode = hasStreamingLLMNode(graphDefinition)

      if (hasStreamingNode) {
        // 使用SSE方式
        realController = executeAgentGraphSSE(id, params, callbacks)
        // 如果在此期间已经调用了 abort，立即中断
        if (isAborted) {
          realController.abort()
        }
      } else {
        // 使用普通方式
        const fakeController = { abort: () => {} }
        realController = fakeController
        
        // 创建安全的函数包装器
        const safeOnStart = typeof callbacks.onStart === 'function' ? callbacks.onStart : () => {}
        const safeOnComplete = typeof callbacks.onComplete === 'function' ? callbacks.onComplete : () => {}
        const safeOnError = typeof callbacks.onError === 'function' ? callbacks.onError : () => {}
        
        try {
          safeOnStart()
          const result = await executeAgentGraph(id, params)
          if (!isAborted) {
            safeOnComplete(result)
          }
        } catch (error) {
          if (!isAborted) {
            safeOnError(error)
          }
        }
      }
    } catch (error) {
      if (!isAborted && callbacks.onError) {
        callbacks.onError(error)
      }
    }
  })

  return controller
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

// ==================== RAG知识库管理 ====================

export function getRAGKnowledgeBases(params) {
  return request.get('/v1/agent/rag/knowledge-bases', { params })
}

export function getRAGKnowledgeBase(id) {
  return request.get(`/v1/agent/rag/knowledge-bases/${id}`)
}

export function createRAGKnowledgeBase(data) {
  return request.post('/v1/agent/rag/knowledge-bases', data)
}

export function updateRAGKnowledgeBase(id, data) {
  return request.put(`/v1/agent/rag/knowledge-bases/${id}`, data)
}

export function deleteRAGKnowledgeBase(id) {
  return request.delete(`/v1/agent/rag/knowledge-bases/${id}`)
}

export function getRAGDocuments(params) {
  return request.get('/v1/agent/rag/documents', { params })
}

export function getRAGDocument(id) {
  return request.get(`/v1/agent/rag/documents/${id}`)
}

export function createRAGDocument(data) {
  return request.post('/v1/agent/rag/documents', data)
}

export function updateRAGDocument(id, data) {
  return request.put(`/v1/agent/rag/documents/${id}`, data)
}

export function deleteRAGDocument(id) {
  return request.delete(`/v1/agent/rag/documents/${id}`)
}

export function processRAGDocument(id, chunk_size = 500, chunk_overlap = 50, split_strategy = "smart") {
    return requestWithLongTimeout.post(`/v1/agent/rag/documents/${id}/process`, null, { params: { chunk_size, chunk_overlap, split_strategy } })
}

export function getRAGDocumentChunks(docId, params) {
  return request.get(`/v1/agent/rag/documents/${docId}/chunks`, { params })
}

export function deleteRAGChunk(id) {
  return request.delete(`/v1/agent/rag/chunks/${id}`)
}

export function searchRAG(data) {
  return requestWithLongTimeout.post('/v1/agent/rag/search', data)
}

export function uploadRAGDocument(knowledgeBaseId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return requestWithLongTimeout.post(`/v1/agent/rag/documents/upload?knowledge_base_id=${knowledgeBaseId}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
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
