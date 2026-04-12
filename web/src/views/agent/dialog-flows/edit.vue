<template>
  <div class="dialog-flow-editor">
    <div class="toolbar">
      <el-button @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <el-divider direction="vertical" />
      <span class="flow-name">{{ dialogFlow?.name || '对话流编辑' }}</span>
      <el-tag :type="getStatusType(dialogFlow?.status)" size="small">{{ getStatusName(dialogFlow?.status) }}</el-tag>
      <div class="toolbar-right">
        <el-button type="primary" @click="saveDialogFlow" :loading="saving">
          <el-icon><Check /></el-icon>
          保存
        </el-button>
        <el-button type="success" @click="executeDialog">
          <el-icon><VideoPlay /></el-icon>
          执行
        </el-button>
      </div>
    </div>
    
    <div class="editor-container">
      <div class="node-panel">
        <div class="panel-title">节点类型</div>
        <div 
          v-for="nodeType in nodeTypes" 
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

    <el-dialog v-model="executeDialogVisible" title="执行对话流" width="600px">
      <el-form label-width="100px">
        <el-form-item label="对话流名称">
          <el-input :value="dialogFlow?.name" disabled />
        </el-form-item>
        <el-form-item label="输入数据">
          <el-input v-model="executeInput" type="textarea" :rows="4" placeholder="JSON格式输入数据" />
        </el-form-item>
        <el-form-item label="执行结果">
          <el-input v-model="executeResult" type="textarea" :rows="6" readonly placeholder="执行结果" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="executeDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="doExecute" :loading="executing">执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  ArrowLeft, Check, VideoPlay, ChatDotRound, QuestionFilled, 
  Share, User, Connection, VideoPlay as Play, CircleCheck, 
  Document, Mic
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
  body: '{}'
})

const nodeTypes = [
  { type: 'start', label: '开始', icon: Play },
  { type: 'end', label: '结束', icon: CircleCheck },
  { type: 'message', label: '消息', icon: ChatDotRound },
  { type: 'text', label: '文本', icon: Document },
  { type: 'voice', label: '语音', icon: Mic },
  { type: 'question', label: '问题', icon: QuestionFilled },
  { type: 'condition', label: '条件判断', icon: Share },
  { type: 'agent', label: '智能体', icon: User },
  { type: 'api', label: 'API调用', icon: Connection }
]

const executeDialogVisible = ref(false)
const executing = ref(false)
const executeInput = ref('{}')
const executeResult = ref('')

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
    api: '🔗'
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
    data: { label: nodeTypes.find(n => n.type === type)?.label || type }
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
      body: nodeConfig.body
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
  executeInput.value = '{}'
  executeResult.value = ''
  executeDialogVisible.value = true
}

const doExecute = async () => {
  executing.value = true
  try {
    const input = JSON.parse(executeInput.value)
    const res = await executeDialogFlow(flowId, input)
    executeResult.value = JSON.stringify(res.data, null, 2)
    ElMessage.success('执行成功')
  } catch (error) {
    executeResult.value = error.message || '执行失败'
    ElMessage.error('执行失败')
  } finally {
    executing.value = false
  }
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
  width: 300px;
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
</style>