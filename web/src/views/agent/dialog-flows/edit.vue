<template>
  <div class="dialog-flow-editor">
    <div class="toolbar">
      <span class="flow-name">{{ dialogFlow?.name || '对话流编辑' }}</span>
      <el-tag :type="getStatusType(dialogFlow?.status)" size="small">{{ getStatusName(dialogFlow?.status) }}</el-tag>
      <div class="toolbar-right">
        <el-button @click="handleImportGraph">
          <el-icon><Upload /></el-icon>
          导入
        </el-button>
        <el-button @click="handleExportGraph">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button type="primary" @click="saveDialogFlow" :loading="saving">
          <el-icon><Check /></el-icon>
          保存
        </el-button>
        <el-button 
          type="warning" 
          @click="publishDialogFlow" 
          v-if="dialogFlow?.status !== 'active'"
        >
          <el-icon><Check /></el-icon>
          发布
        </el-button>
        <el-button type="success" @click="executeDialog">
          <el-icon><VideoPlay /></el-icon>
          执行
        </el-button>
      </div>
    </div>
    
    <div class="editor-container">
      <div class="node-panel">
        <div class="panel-title">流程控制</div>
        <div 
          v-for="nodeType in nodeCategories.flowControl" 
          :key="nodeType.type"
          class="node-item"
          draggable="true"
          @dragstart="onDragStart($event, nodeType.type)"
        >
          <el-icon :size="20"><component :is="nodeType.icon" /></el-icon>
          <span>{{ nodeType.label }}</span>
        </div>
        
        <div class="panel-title" style="margin-top: 20px">输入输出</div>
        <div 
          v-for="nodeType in nodeCategories.inputOutput" 
          :key="nodeType.type"
          class="node-item"
          draggable="true"
          @dragstart="onDragStart($event, nodeType.type)"
        >
          <el-icon :size="20"><component :is="nodeType.icon" /></el-icon>
          <span>{{ nodeType.label }}</span>
        </div>
        
        <div class="panel-title" style="margin-top: 20px">内容展示</div>
        <div 
          v-for="nodeType in nodeCategories.content" 
          :key="nodeType.type"
          class="node-item"
          draggable="true"
          @dragstart="onDragStart($event, nodeType.type)"
        >
          <el-icon :size="20"><component :is="nodeType.icon" /></el-icon>
          <span>{{ nodeType.label }}</span>
        </div>
        
        <div class="panel-title" style="margin-top: 20px">功能调用</div>
        <div 
          v-for="nodeType in nodeCategories.functions" 
          :key="nodeType.type"
          class="node-item"
          draggable="true"
          @dragstart="onDragStart($event, nodeType.type)"
        >
          <el-icon :size="20"><component :is="nodeType.icon" /></el-icon>
          <span>{{ nodeType.label }}</span>
        </div>
        
        <div class="panel-title" style="margin-top: 20px">操作提示</div>
        <div class="help-text">
          <p>• 拖拽节点到画布创建</p>
          <p>• 点击节点选中并配置</p>
          <p>• 从右侧连接点拖拽到左侧连接点连线</p>
          <p>• 点击连线可删除</p>
        </div>
      </div>
      
      <div class="flow-container" @dragover="onDragOver" @drop="onDrop" @mousemove="onMouseMove" @mouseup="onMouseUp">
        <div class="canvas" ref="canvas">
          <svg class="edges-svg">
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                <polygon points="0 0, 10 3, 0 6" fill="#409eff" />
              </marker>
            </defs>
            <g v-for="edge in edges" :key="edge.id" @click="onEdgeClick(edge)">
              <path
                :d="getEdgePath(edge)"
                class="workflow-edge"
                :class="{ 'selected': selectedEdge?.id === edge.id }"
                marker-end="url(#arrowhead)"
              />
            </g>
            <path v-if="drawingEdge" :d="tempEdgePath" class="temp-edge" />
          </svg>
          
          <div 
            v-for="node in nodes" 
            :key="node.id"
            class="workflow-node"
            :class="{ 
              'selected': selectedNode?.id === node.id,
              [node.type + '-node']: true 
            }"
            @click="onNodeClick(node)"
            @mousedown="onNodeMouseDown($event, node)"
            :style="{ left: node.position.x + 'px', top: node.position.y + 'px' }"
          >
            <div class="connection-point input" 
                 @mousedown.stop="onInputPointMouseDown($event, node)"
                 @mouseup="onInputPointMouseUp($event, node)">
            </div>
            <div class="node-header">
              <span class="node-icon">{{ getNodeIcon(node.type) }}</span>
              <span class="node-label">{{ node.data.label }}</span>
            </div>
            <div class="node-content" v-if="node.data.content || node.data.text || node.data.question || node.data.url">{{ getNodeContent(node) }}</div>
            <div class="connection-point output"
                 @mousedown.stop="onOutputPointMouseDown($event, node)">
            </div>
          </div>
        </div>
      </div>
      
      <div class="config-panel" v-if="selectedNode || selectedEdge">
        <template v-if="selectedNode">
          <div class="panel-title">节点配置</div>
          <el-form :model="nodeConfig" label-width="80px" size="small">
            <el-form-item label="节点名称">
              <el-input v-model="nodeConfig.label" @change="updateNodeLabel" />
            </el-form-item>
            
            <!-- 下一步节点配置 -->
            <el-divider content-position="left">下一步节点配置</el-divider>
            <el-form-item label="目标节点">
              <div class="target-nodes-container" style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; border: 1px solid #e0e0e0;">
                <div v-if="targetNodes.length === 0" style="text-align: center; color: #909399; padding: 20px;">
                  无目标节点
                </div>
                <div v-else class="target-nodes-list">
                  <div v-for="(node, index) in targetNodes" :key="node.id" class="target-node-item" style="display: flex; align-items: center; margin-bottom: 10px; padding: 8px 12px; background-color: #fff; border-radius: 4px; border: 1px solid #e0e0e0;">
                    <el-icon :size="16" style="color: #409eff; margin-right: 8px;">
                      <component :is="allNodeTypes.find(n => n.type === node.type)?.icon || Document" />
                    </el-icon>
                    <span style="flex: 1; color: #303133;">{{ node.data.label }}</span>
                    <el-tag size="small" type="info" style="margin-left: 10px;">
                      {{ node.type }}
                    </el-tag>
                  </div>
                </div>
              </div>
            </el-form-item>
            
            <template v-if="selectedNode.type === 'message'">
              <el-form-item label="消息内容">
                <el-input v-model="nodeConfig.content" type="textarea" :rows="4" @change="updateNodeData" placeholder="输入消息内容，支持变量 {{变量名}}" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'question'">
              <el-form-item label="问题内容">
                <el-input v-model="nodeConfig.question" type="textarea" :rows="3" @change="updateNodeData" />
              </el-form-item>
              <el-form-item label="变量名">
                <el-input v-model="nodeConfig.variable" @change="updateNodeData" placeholder="存储回答的变量名" />
              </el-form-item>
              <el-form-item label="选项">
                <el-input v-model="nodeConfig.options" type="textarea" :rows="2" @change="updateNodeData" placeholder="选项列表，逗号分隔" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'condition'">
              <el-form-item label="条件表达式">
                <el-input v-model="nodeConfig.condition" type="textarea" :rows="3" @change="updateNodeData" placeholder="如: {{score}} > 60" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'agent'">
              <el-form-item label="选择智能体">
                <el-select v-model="nodeConfig.agent_id" placeholder="请选择" @change="updateNodeData" style="width: 100%">
                  <el-option v-for="agent in agents" :key="agent.id" :label="agent.name" :value="agent.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="输入变量">
                <el-input v-model="nodeConfig.input_variable" @change="updateNodeData" placeholder="输入变量名" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'api'">
              <el-form-item label="API URL">
                <el-input v-model="nodeConfig.url" @change="updateNodeData" placeholder="API地址" />
              </el-form-item>
              <el-form-item label="请求方法">
                <el-select v-model="nodeConfig.method" @change="updateNodeData" style="width: 100%">
                  <el-option label="GET" value="GET" />
                  <el-option label="POST" value="POST" />
                  <el-option label="PUT" value="PUT" />
                  <el-option label="DELETE" value="DELETE" />
                </el-select>
              </el-form-item>
              <el-form-item label="请求头">
                <el-input v-model="nodeConfig.headers" type="textarea" :rows="2" @change="updateNodeData" placeholder="JSON格式" />
              </el-form-item>
              <el-form-item label="请求体">
                <el-input v-model="nodeConfig.body" type="textarea" :rows="3" @change="updateNodeData" placeholder="JSON格式" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'text'">
              <el-form-item label="文本内容">
                <el-input v-model="nodeConfig.content" type="textarea" :rows="4" @change="updateNodeData" placeholder="输入文本内容，支持变量 {{变量名}}" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'voice'">
              <el-form-item label="语音文本">
                <el-input v-model="nodeConfig.text" type="textarea" :rows="3" @change="updateNodeData" placeholder="输入要转换的文本内容" />
              </el-form-item>
              <el-form-item label="语音类型">
                <el-select v-model="nodeConfig.voice_type" @change="updateNodeData" style="width: 100%">
                  <el-option label="文本转语音" value="tts" />
                  <el-option label="语音识别" value="asr" />
                </el-select>
              </el-form-item>
              <el-form-item label="语言">
                <el-select v-model="nodeConfig.language" @change="updateNodeData" style="width: 100%">
                  <el-option label="中文" value="zh-CN" />
                  <el-option label="英文" value="en-US" />
                </el-select>
              </el-form-item>
            </template>
            
            <!-- 知识检索节点配置 -->
            <template v-if="selectedNode.type === 'knowledge_retrieval'">
              <el-form-item label="知识库">
                <el-select v-model="nodeConfig.knowledge_base" @change="updateNodeData" style="width: 100%">
                  <el-option label="默认知识库" value="default" />
                  <el-option label="用户知识库" value="user" />
                </el-select>
              </el-form-item>
              <el-form-item label="检索查询">
                <el-input v-model="nodeConfig.query" type="textarea" :rows="2" @change="updateNodeData" placeholder="检索关键词或语句" />
              </el-form-item>
              <el-form-item label="检索数量">
                <el-input-number v-model="nodeConfig.top_k" :min="1" :max="100" @change="updateNodeData" />
              </el-form-item>
              <el-form-item label="相似度阈值">
                <el-slider v-model="nodeConfig.similarity_threshold" :min="0" :max="1" :step="0.1" @change="updateNodeData" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="nodeConfig.output_var" @change="updateNodeData" placeholder="存储检索结果的变量名" />
              </el-form-item>
            </template>
            
            <!-- 输入节点配置 -->
            <template v-if="selectedNode.type === 'input'">
              <el-form-item label="输入类型">
                <el-select v-model="nodeConfig.input_type" @change="updateNodeData" style="width: 100%">
                  <el-option label="文本" value="text" />
                  <el-option label="文件" value="file" />
                  <el-option label="表单" value="form" />
                </el-select>
              </el-form-item>
              <el-form-item label="输入提示">
                <el-input v-model="nodeConfig.input_placeholder" @change="updateNodeData" placeholder="用户输入提示" />
              </el-form-item>
            </template>
            
            <!-- 输出节点配置 -->
            <template v-if="selectedNode.type === 'output'">
              <el-form-item label="输出类型">
                <el-select v-model="nodeConfig.output_type" @change="updateNodeData" style="width: 100%">
                  <el-option label="文本" value="text" />
                  <el-option label="JSON" value="json" />
                  <el-option label="文件" value="file" />
                </el-select>
              </el-form-item>
              <el-form-item label="输出内容">
                <el-input v-model="nodeConfig.output_content" type="textarea" :rows="4" @change="updateNodeData" placeholder="输出内容或变量表达式" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="nodeConfig.output_var" @change="updateNodeData" placeholder="存储输出结果的变量名" />
              </el-form-item>
            </template>
            
          </el-form>
          
          <el-button type="danger" size="small" @click="deleteSelectedNode" style="width: 100%; margin-top: 10px;">
            删除节点
          </el-button>
        </template>
        
        <template v-if="selectedEdge">
          <div class="panel-title">连线配置</div>
          <div class="edge-info">
            <p><strong>源节点：</strong>{{ getNodeById(selectedEdge.source)?.data.label }}</p>
            <p><strong>目标节点：</strong>{{ getNodeById(selectedEdge.target)?.data.label }}</p>
          </div>
          <el-button type="danger" size="small" @click="deleteSelectedEdge" style="width: 100%">
            删除连线
          </el-button>
        </template>
      </div>
    </div>

    <el-dialog v-model="executeDialogVisible" title="执行对话流" width="900px" class="wechat-style-dialog">
      <div class="chat-container">
        <!-- 聊天历史 -->
        <div class="chat-messages">
          <div
            v-for="(msg, index) in dialogHistory"
            :key="index"
            :class="['message', msg.role]"
          >
            <div class="message-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
            <div class="message-content-wrapper">
              <div class="message-role">{{ msg.role === 'user' ? '用户' : 'AI' }}</div>
              <div class="message-content">{{ msg.content }}</div>
              <div class="message-time">{{ msg.time }}</div>
              
              <!-- AI的思考、行动、观察、结果 - 可折叠 -->
              <div v-if="msg.role === 'assistant' && msg.process && msg.process.length > 0" class="message-process">
                <div
                  v-for="(process, pIndex) in msg.process"
                  :key="pIndex"
                  :class="['process-item', process.type, { collapsed: process.collapsed }]"
                >
                  <div class="process-header" @click="process.collapsed = !process.collapsed">
                    <span class="process-label">{{ process.label }}</span>
                    <span class="process-time">{{ process.time }}</span>
                    <span class="collapse-icon">{{ process.collapsed ? '▶' : '▼' }}</span>
                  </div>
                  <div class="process-content" v-show="!process.collapsed">{{ process.content }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="chat-input-area">
          <el-input
            v-model="currentInput"
            type="textarea"
            :rows="3"
            placeholder="请输入你要说的话..."
            @keyup.enter.ctrl="doExecute"
            class="input-textarea"
          />
          <div class="input-actions">
            <el-button @click="clearDialogHistory" :disabled="dialogHistory.length === 0">清空历史</el-button>
            <el-button @click="executeDialogVisible = false">关闭</el-button>
            <el-button type="primary" @click="doExecute" :loading="executing">发送</el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  ArrowLeft, Check, VideoPlay, ChatDotRound, QuestionFilled, 
  Share, User, Connection, VideoPlay as Play, CircleCheck, 
  Document, Mic, Upload, Download
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDialogFlow, updateDialogFlow, executeDialogFlow } from '@/api/agent'
import { getAgents } from '@/api/agent'

const route = useRoute()
const router = useRouter()

const flowId = route.params.id
const dialogFlow = ref(null)
const saving = ref(false)
const agents = ref([])

const nodes = ref([])
const edges = ref([])
const selectedNode = ref(null)
const selectedEdge = ref(null)

// 计算当前节点的实际目标节点列表
const targetNodes = computed(() => {
  if (!selectedNode.value) return []
  // 找到所有以当前节点为源节点的边
  const nodeEdges = edges.value.filter(edge => edge.source === selectedNode.value.id)
  // 对于每条边，找到对应的目标节点
  return nodeEdges.map(edge => {
    const targetNode = getNodeById(edge.target)
    return targetNode || { id: edge.target, data: { label: '未知节点' } }
  })
})

const nodeConfig = reactive({
  label: '',
  content: '',
  text: '',
  voice_type: 'tts',
  language: 'zh-CN',
  question: '',
  variable: '',
  options: '',
  condition: '',
  agent_id: null,
  input_variable: '',
  url: '',
  method: 'GET',
  headers: '{}',
  body: '{}',
  // 输入节点配置
  input_type: 'text',
  input_placeholder: '',
  // 知识检索节点配置
  knowledge_base: 'default',
  query: '',
  top_k: 5,
  similarity_threshold: 0.7,
  // 输出节点配置
  output_type: 'text',
  output_content: '',
  output_var: ''
})

const nodeCategories = {
  flowControl: [
    { type: 'start', label: '开始', icon: Play, next: ['input', 'message', 'text', 'voice', 'question', 'agent', 'api', 'knowledge_retrieval'] },
    { type: 'end', label: '结束', icon: CircleCheck, next: [] },
    { type: 'condition', label: '条件判断', icon: Share, next: ['message', 'text', 'voice', 'question', 'agent', 'api', 'knowledge_retrieval', 'output'] }
  ],
  inputOutput: [
    { type: 'input', label: '输入', icon: Document, next: ['message', 'text', 'voice', 'question', 'agent', 'api', 'knowledge_retrieval'] },
    { type: 'output', label: '输出', icon: CircleCheck, next: ['end'] }
  ],
  content: [
    { type: 'message', label: '消息', icon: ChatDotRound, next: ['text', 'voice', 'question', 'agent', 'api', 'knowledge_retrieval', 'output'] },
    { type: 'text', label: '文本', icon: Document, next: ['message', 'voice', 'question', 'agent', 'api', 'knowledge_retrieval', 'output'] },
    { type: 'voice', label: '语音', icon: Mic, next: ['message', 'text', 'question', 'agent', 'api', 'knowledge_retrieval', 'output'] },
    { type: 'question', label: '问题', icon: QuestionFilled, next: ['message', 'text', 'voice', 'agent', 'api', 'knowledge_retrieval', 'output'] }
  ],
  functions: [
    { type: 'agent', label: '智能体', icon: User, next: ['message', 'text', 'voice', 'question', 'agent', 'api', 'knowledge_retrieval', 'output'] },
    { type: 'api', label: 'API调用', icon: Connection, next: ['message', 'text', 'voice', 'question', 'agent', 'knowledge_retrieval', 'output'] },
    { type: 'knowledge_retrieval', label: '知识检索', icon: Document, next: ['message', 'text', 'voice', 'question', 'agent', 'api', 'output'] }
  ]
}

const allNodeTypes = [
  ...nodeCategories.flowControl,
  ...nodeCategories.inputOutput,
  ...nodeCategories.content,
  ...nodeCategories.functions
]

const executeDialogVisible = ref(false)
const executing = ref(false)
const executeInput = ref('')
const executeResult = ref('')
const dialogHistory = ref([])
const currentInput = ref('')
const latestResponse = ref('')

const drawingEdge = ref(false)
const edgeStartNode = ref(null)
const edgeStartPoint = ref({ x: 0, y: 0 })
const currentMousePos = ref({ x: 0, y: 0 })

const draggingNode = ref(null)
const dragOffset = ref({ x: 0, y: 0 })

const tempEdgePath = computed(() => {
  if (!drawingEdge.value) return ''
  return `M ${edgeStartPoint.value.x} ${edgeStartPoint.value.y} L ${currentMousePos.value.x} ${currentMousePos.value.y}`
})

const statusMap = { draft: '草稿', active: '启用', inactive: '禁用' }
const getStatusName = (status) => statusMap[status] || status
const getStatusType = (status) => {
  const map = { draft: 'info', active: 'success', inactive: 'danger' }
  return map[status] || ''
}

const getNodeIcon = (type) => {
  const icons = {
    start: '▶️',
    end: '⏹️',
    message: '💬',
    text: '📝',
    voice: '🎤',
    question: '❓',
    condition: '🔀',
    agent: '🤖',
    api: '🔗',
    knowledge_retrieval: '📚',
    output: '📤'
  }
  return icons[type] || '📦'
}

const getNodeContent = (node) => {
  if (node.data.content) return node.data.content
  if (node.data.text) return node.data.text
  if (node.data.question) return node.data.question
  if (node.data.url) return node.data.url
  return ''
}

const getNodeById = (id) => {
  return nodes.value.find(n => n.id === id)
}

const getEdgePath = (edge) => {
  const sourceNode = getNodeById(edge.source)
  const targetNode = getNodeById(edge.target)
  
  if (!sourceNode || !targetNode) return ''
  
  const sourceX = sourceNode.position.x + 150
  const sourceY = sourceNode.position.y + 20
  const targetX = targetNode.position.x
  const targetY = targetNode.position.y + 20
  
  const midX = (sourceX + targetX) / 2
  
  return `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`
}

const goBack = () => {
  router.push('/panel/agent/dialog-flows')
}

const fetchDialogFlow = async () => {
  try {
    const res = await getDialogFlow(flowId)
    dialogFlow.value = res.data
    if (res.data.flow_data) {
      nodes.value = res.data.flow_data.nodes || []
      edges.value = res.data.flow_data.edges || []
    } else if (res.data.definition) {
      nodes.value = res.data.definition.nodes || []
      edges.value = res.data.definition.edges || []
    }
  } catch (error) {
    ElMessage.error('获取对话流失败')
    console.error(error)
  }
}

const fetchAgents = async () => {
  try {
    const res = await getAgents({ limit: 1000 })
    agents.value = res.data?.items || res.data || []
  } catch (error) {
    console.error(error)
  }
}

const saveDialogFlow = async () => {
  saving.value = true
  try {
    await updateDialogFlow(flowId, {
      flow_data: { nodes: nodes.value, edges: edges.value }
    })
    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  } finally {
    saving.value = false
  }
}

const publishDialogFlow = async () => {
  saving.value = true
  try {
    await updateDialogFlow(flowId, {
      status: 'active',
      flow_data: { nodes: nodes.value, edges: edges.value }
    })
    dialogFlow.value.status = 'active'
    ElMessage.success('发布成功')
  } catch (error) {
    ElMessage.error('发布失败')
    console.error(error)
  } finally {
    saving.value = false
  }
}

const onDragStart = (event, nodeType) => {
  event.dataTransfer.setData('nodeType', nodeType)
  event.dataTransfer.effectAllowed = 'move'
}

const onDragOver = (event) => {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

const onDrop = (event) => {
  const type = event.dataTransfer.getData('nodeType')
  if (!type) return
  
  const canvas = event.currentTarget
  const rect = canvas.getBoundingClientRect()
  const position = {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  }
  
  const newNode = {
    id: `${type}-${Date.now()}`,
    type,
    position,
    data: { label: allNodeTypes.find(n => n.type === type)?.label || type }
  }
  nodes.value.push(newNode)
}

const onNodeClick = (node) => {
  selectedEdge.value = null
  selectedNode.value = node
  nodeConfig.label = node.data.label || ''
  nodeConfig.content = node.data.content || ''
  nodeConfig.text = node.data.text || ''
  nodeConfig.voice_type = node.data.voice_type || 'tts'
  nodeConfig.language = node.data.language || 'zh-CN'
  nodeConfig.question = node.data.question || ''
  nodeConfig.variable = node.data.variable || ''
  nodeConfig.options = node.data.options || ''
  nodeConfig.condition = node.data.condition || ''
  nodeConfig.agent_id = node.data.agent_id || null
  nodeConfig.input_variable = node.data.input_variable || ''
  nodeConfig.url = node.data.url || ''
  nodeConfig.method = node.data.method || 'GET'
  nodeConfig.headers = node.data.headers || '{}'
  nodeConfig.body = node.data.body || '{}'
  // 输入节点配置
  nodeConfig.input_type = node.data.input_type || 'text'
  nodeConfig.input_placeholder = node.data.input_placeholder || ''
  // 知识检索节点配置
  nodeConfig.knowledge_base = node.data.knowledge_base || 'default'
  nodeConfig.query = node.data.query || ''
  nodeConfig.top_k = node.data.top_k || 5
  nodeConfig.similarity_threshold = node.data.similarity_threshold || 0.7
  // 输出节点配置
  nodeConfig.output_var = node.data.output_var || ''
  nodeConfig.output_type = node.data.output_type || 'text'
  nodeConfig.output_content = node.data.output_content || ''
}

const onNodeMouseDown = (event, node) => {
  if (event.target.classList.contains('connection-point')) return
  
  draggingNode.value = node
  const canvas = event.currentTarget.closest('.canvas')
  const rect = canvas.getBoundingClientRect()
  dragOffset.value = {
    x: event.clientX - rect.left - node.position.x,
    y: event.clientY - rect.top - node.position.y
  }
  event.preventDefault()
}

const onEdgeClick = (edge) => {
  selectedNode.value = null
  selectedEdge.value = edge
}

const onOutputPointMouseDown = (event, node) => {
  drawingEdge.value = true
  edgeStartNode.value = node
  edgeStartPoint.value = {
    x: node.position.x + 150,
    y: node.position.y + 20
  }
  currentMousePos.value = { ...edgeStartPoint.value }
}

const onInputPointMouseUp = (event, node) => {
  if (drawingEdge.value && edgeStartNode.value && edgeStartNode.value.id !== node.id) {
    const exists = edges.value.find(e => 
      e.source === edgeStartNode.value.id && e.target === node.id
    )
    
    if (!exists) {
      const newEdge = {
        id: `edge-${Date.now()}`,
        source: edgeStartNode.value.id,
        target: node.id
      }
      edges.value.push(newEdge)
      ElMessage.success('连线创建成功')
    } else {
      ElMessage.warning('连线已存在')
    }
  }
  
  drawingEdge.value = false
  edgeStartNode.value = null
}

const onMouseMove = (event) => {
  if (drawingEdge.value) {
    const canvas = event.currentTarget
    const rect = canvas.getBoundingClientRect()
    currentMousePos.value = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    }
  }
  
  if (draggingNode.value) {
    const canvas = event.currentTarget
    const rect = canvas.getBoundingClientRect()
    draggingNode.value.position = {
      x: event.clientX - rect.left - dragOffset.value.x,
      y: event.clientY - rect.top - dragOffset.value.y
    }
  }
}

const onMouseUp = () => {
  drawingEdge.value = false
  edgeStartNode.value = null
  draggingNode.value = null
}

const updateNodeLabel = () => {
  if (selectedNode.value) {
    selectedNode.value.data.label = nodeConfig.label
  }
}

const updateNodeData = () => {
  if (selectedNode.value) {
    selectedNode.value.data = {
      ...selectedNode.value.data,
      label: nodeConfig.label,
      content: nodeConfig.content,
      text: nodeConfig.text,
      voice_type: nodeConfig.voice_type,
      language: nodeConfig.language,
      question: nodeConfig.question,
      variable: nodeConfig.variable,
      options: nodeConfig.options,
      condition: nodeConfig.condition,
      agent_id: nodeConfig.agent_id,
      input_variable: nodeConfig.input_variable,
      url: nodeConfig.url,
      method: nodeConfig.method,
      headers: nodeConfig.headers,
      body: nodeConfig.body,
      // 输入节点配置
      input_type: nodeConfig.input_type,
      input_placeholder: nodeConfig.input_placeholder,
      // 知识检索节点配置
      knowledge_base: nodeConfig.knowledge_base,
      query: nodeConfig.query,
      top_k: nodeConfig.top_k,
      similarity_threshold: nodeConfig.similarity_threshold,
      // 输出节点配置
      output_var: nodeConfig.output_var,
      output_type: nodeConfig.output_type,
      output_content: nodeConfig.output_content
    }
  }
}

const deleteSelectedNode = () => {
  if (selectedNode.value) {
    edges.value = edges.value.filter(e => 
      e.source !== selectedNode.value.id && e.target !== selectedNode.value.id
    )
    
    const index = nodes.value.findIndex(n => n.id === selectedNode.value.id)
    if (index > -1) {
      nodes.value.splice(index, 1)
    }
    selectedNode.value = null
    ElMessage.success('节点已删除')
  }
}

const deleteSelectedEdge = () => {
  if (selectedEdge.value) {
    const index = edges.value.findIndex(e => e.id === selectedEdge.value.id)
    if (index > -1) {
      edges.value.splice(index, 1)
    }
    selectedEdge.value = null
    ElMessage.success('连线已删除')
  }
}

const executeDialog = () => {
  executeInput.value = ''
  executeResult.value = ''
  // 清空之前的输入和回复，但保留对话历史
  currentInput.value = ''
  latestResponse.value = ''
  executeDialogVisible.value = true
}

const clearDialogHistory = () => {
  dialogHistory.value = []
  currentInput.value = ''
  latestResponse.value = ''
  ElMessage.success('对话历史已清空')
}

const doExecute = async () => {
  if (!currentInput.value.trim()) {
    ElMessage.warning('请输入内容')
    return
  }
  
  executing.value = true
  try {
    // 添加用户输入到历史
    const userMessage = {
      role: 'user',
      content: currentInput.value,
      time: new Date().toLocaleTimeString('zh-CN')
    }
    dialogHistory.value.push(userMessage)
    
    // 准备输入数据 - 包含对话历史
    const input = {
      text: currentInput.value,
      history: [...dialogHistory.value]
    }
    
    const res = await executeDialogFlow(flowId, input)
    
    // 解析执行结果
    let assistantResponse = ''
    if (typeof res.data === 'string') {
      assistantResponse = res.data
    } else if (res.data.output || res.data.result || res.data.text || res.data.response) {
      assistantResponse = res.data.output || res.data.result || res.data.text || res.data.response
    } else if (res.data.variables) {
      // 尝试从变量中获取结果
      const vars = res.data.variables
      assistantResponse = vars.final_report || vars.response || vars.text || vars.output || JSON.stringify(vars, null, 2)
    } else {
      assistantResponse = JSON.stringify(res.data, null, 2)
    }
    
    // 添加助手回复到历史
    const assistantMessage = {
      role: 'assistant',
      content: assistantResponse,
      time: new Date().toLocaleTimeString('zh-CN')
    }
    dialogHistory.value.push(assistantMessage)
    
    // 更新最新回复
    latestResponse.value = assistantResponse
    
    // 清空输入框
    currentInput.value = ''
    
    // 保存原始执行结果
    executeResult.value = JSON.stringify(res.data, null, 2)
    
    ElMessage.success('发送成功')
  } catch (error) {
    // 即使出错也要显示错误
    const errorMessage = {
      role: 'assistant',
      content: '执行失败: ' + (error.message || '未知错误'),
      time: new Date().toLocaleTimeString('zh-CN')
    }
    dialogHistory.value.push(errorMessage)
    latestResponse.value = errorMessage.content
    executeResult.value = error.message || '执行失败'
    ElMessage.error('执行失败')
  } finally {
    executing.value = false
  }
}

const handleExportGraph = () => {
  const graphData = {
    nodes: nodes.value,
    edges: edges.value,
    name: dialogFlow.value?.name || 'dialog-flow',
    description: dialogFlow.value?.description || ''
  }
  const blob = new Blob([JSON.stringify(graphData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${dialogFlow.value?.name || 'dialog-flow'}-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('图结构导出成功')
}

const handleImportGraph = () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = (e) => {
    const file = e.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (event) => {
        try {
          const data = JSON.parse(event.target.result)
          if (data.nodes && data.edges) {
            nodes.value = data.nodes
            edges.value = data.edges
            ElMessage.success('图结构导入成功')
          } else {
            ElMessage.error('文件格式错误，缺少nodes或edges字段')
          }
        } catch (error) {
          ElMessage.error('导入失败：文件格式错误')
          console.error(error)
        }
      }
      reader.readAsText(file)
    }
  }
  input.click()
}

onMounted(() => {
  fetchDialogFlow()
  fetchAgents()
})
</script>

<style scoped>
.dialog-flow-editor {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

/* 对话历史样式 */
.dialog-history-container {
  max-height: 300px;
  overflow-y: auto;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
}

.dialog-turn {
  margin-bottom: 12px;
  padding: 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.dialog-turn:last-child {
  margin-bottom: 0;
}

.turn-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.turn-time {
  font-size: 12px;
  color: #909399;
}

.turn-content {
  font-size: 14px;
  color: #303133;
  line-height: 1.6;
  word-wrap: break-word;
}

.latest-response-container {
  background: #f0f9ff;
  border: 1px solid #b3d8ff;
  border-radius: 8px;
  padding: 12px;
}

.response-content {
  font-size: 14px;
  color: #303133;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.toolbar {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  gap: 10px;
}

.flow-name {
  font-size: 16px;
  font-weight: 500;
}

.toolbar-right {
  margin-left: auto;
  display: flex;
  gap: 10px;
}

.editor-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.node-panel {
  width: 200px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  padding: 10px;
  overflow-y: auto;
  max-height: 100%;
}

.panel-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e4e7ed;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  cursor: grab;
  transition: all 0.2s;
}

.node-item:hover {
  background: #e6f0ff;
  border-color: #409eff;
}

.help-text {
  font-size: 12px;
  color: #909399;
  line-height: 1.8;
}

.flow-container {
  flex: 1;
  background: #fff;
  position: relative;
  overflow: auto;
}

.canvas {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 600px;
  background: #fafafa;
  background-image: 
    linear-gradient(rgba(0, 0, 0, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.05) 1px, transparent 1px);
  background-size: 20px 20px;
}

.edges-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.workflow-edge {
  fill: none;
  stroke: #409eff;
  stroke-width: 2;
  cursor: pointer;
  pointer-events: stroke;
  transition: stroke-width 0.2s;
}

.workflow-edge:hover,
.workflow-edge.selected {
  stroke-width: 3;
  stroke: #f56c6c;
}

.temp-edge {
  fill: none;
  stroke: #409eff;
  stroke-width: 2;
  stroke-dasharray: 5, 5;
  pointer-events: none;
}

.workflow-node {
  position: absolute;
  padding: 10px 15px;
  border-radius: 8px;
  background: #fff;
  border: 2px solid #e4e7ed;
  min-width: 120px;
  cursor: move;
  transition: all 0.2s;
  user-select: none;
}

.workflow-node:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.workflow-node.selected {
  border-color: #409eff;
  box-shadow: 0 0 10px rgba(64, 158, 255, 0.3);
}

.start-node {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
  color: #fff;
  border-color: #43e97b;
}

.end-node {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
  color: #fff;
  border-color: #fa709a;
}

.message-node {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: #667eea;
}

.text-node {
  background: linear-gradient(135deg, #a8caba 0%, #5d4e75 100%);
  color: #fff;
  border-color: #a8caba;
}

.voice-node {
  background: linear-gradient(135deg, #fccb90 0%, #d57eeb 100%);
  color: #333;
  border-color: #fccb90;
}

.question-node {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: #fff;
  border-color: #f093fb;
}

.condition-node {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: #fff;
  border-color: #4facfe;
}

.agent-node {
  background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
  color: #333;
  border-color: #a8edea;
}

.api-node {
  background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%);
  color: #333;
  border-color: #d299c2;
}

.input-node {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: #667eea;
}

.output-node {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: #fff;
  border-color: #f093fb;
}

.knowledge_retrieval-node {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: #667eea;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-icon {
  font-size: 16px;
}

.node-label {
  font-size: 14px;
  font-weight: 500;
}

.node-content {
  font-size: 12px;
  margin-top: 5px;
  opacity: 0.9;
  word-break: break-all;
  line-height: 1.4;
}

.connection-point {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #409eff;
  border: 2px solid #fff;
  border-radius: 50%;
  cursor: crosshair;
  transition: all 0.2s;
  z-index: 10;
}

.connection-point:hover {
  transform: scale(1.3);
  background: #67c23a;
}

.connection-point.input {
  left: -6px;
  top: 50%;
  transform: translateY(-50%);
}

.connection-point.input:hover {
  transform: translateY(-50%) scale(1.3);
}

.connection-point.output {
  right: -6px;
  top: 50%;
  transform: translateY(-50%);
}

.connection-point.output:hover {
  transform: translateY(-50%) scale(1.3);
}

.config-panel {
  width: 350px;
  min-width: 300px;
  max-width: 400px;
  background: #fff;
  border-left: 1px solid #e4e7ed;
  padding: 10px;
  overflow-y: auto;
}

.edge-info {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 10px;
}

.edge-info p {
  margin: 5px 0;
  font-size: 13px;
}

/* 微信风格对话框 */
.wechat-style-dialog .el-dialog__body {
  padding: 0;
  height: 600px;
  overflow: hidden;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding:20px;
}

/* 聊天消息 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  min-height:300px;
  background: #f5f7fa;
}

.message {
  display: flex;
  margin-bottom: 20px;
  animation: messageFadeIn 0.3s ease;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  font-size: 32px;
  margin: 0 10px;
  flex-shrink: 0;
}

.message-content-wrapper {
  max-width: 70%;
  display: flex;
  flex-direction: column;
}

.message-role {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #909399;
}

.message-content {
  padding: 12px 16px;
  border-radius: 18px;
  line-height: 1.5;
  word-wrap: break-word;
}

.message.user .message-content {
  background: #91d5ff;
  color: #303133;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background: #fff;
  color: #303133;
  border-bottom-left-radius: 4px;
  border: 1px solid #e4e7ed;
}

.message-time {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 4px;
  align-self: flex-end;
}

/* 处理过程 */
.message-process {
  margin-top: 10px;
  padding: 10px;
  background: #f0f2f5;
  border-radius: 8px;
  font-size: 13px;
}

.process-item {
  margin-bottom: 8px;
  padding: 8px;
  background: #fff;
  border-radius: 6px;
  border-left: 3px solid #409eff;
  transition: all 0.3s ease;
}

.process-item.collapsed {
  background: #f5f7fa;
}

.process-item.thinking {
  border-left-color: #e6a23c;
}

.process-item.action {
  border-left-color: #409eff;
}

.process-item.result {
  border-left-color: #67c23a;
}

.process-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  cursor: pointer;
  user-select: none;
}

.process-header:hover {
  background: #f0f2f5;
  margin: -4px;
  padding: 4px 8px;
  border-radius: 4px;
}

.process-label {
  font-weight: 600;
  font-size: 12px;
  color: #303133;
}

.process-time {
  font-size: 11px;
  color: #c0c4cc;
  margin-left: 8px;
}

.collapse-icon {
  font-size: 10px;
  color: #909399;
  margin-left: 8px;
  transition: transform 0.3s ease;
}

.process-content {
  font-size: 12px;
  color: #606266;
  line-height: 1.4;
  word-wrap: break-word;
  padding-top: 4px;
}

/* 输入区 */
.chat-input-area {
  padding-top: 20px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
}

.input-textarea {
  margin-bottom: 10px;
  border-radius: 8px;
  resize: none;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 动画 */
@keyframes messageFadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
