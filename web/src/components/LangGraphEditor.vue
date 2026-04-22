<template>
  <div class="langgraph-editor">
    <div class="toolbar">
      <span class="title">{{ title || 'LangGraph 工作流编辑器' }}</span>
      <div class="toolbar-right">
        <el-button @click="exportWorkflow" :icon="Download">导出</el-button>
        <el-button @click="importWorkflow" :icon="Upload">导入</el-button>
        <el-button type="primary" @click="saveWorkflow" :loading="saving" :icon="Check">保存</el-button>
        <el-button type="success" @click="executeWorkflowDialog" :loading="executing" :icon="VideoPlay">执行</el-button>
      </div>
    </div>

    <div class="editor-content">
      <div class="node-sidebar">
        <div class="sidebar-header">节点库</div>
        
        <div class="node-category" v-for="category in nodeCategories" :key="category.name">
          <div class="category-title">{{ category.name }}</div>
          <div 
            v-for="nodeType in category.nodes" 
            :key="nodeType.type"
            class="node-item"
            :draggable="true"
            @dragstart="onDragStart($event, nodeType.type)"
          >
            <el-icon :size="18"><component :is="nodeType.icon" /></el-icon>
            <span>{{ nodeType.label }}</span>
          </div>
        </div>

        <div class="help-section">
          <div class="sidebar-header">操作说明</div>
          <ul>
            <li>拖拽节点到画布创建</li>
            <li>点击节点选中并配置</li>
            <li>从右侧连接点拖拽连线</li>
            <li>点击连线可删除</li>
          </ul>
        </div>
      </div>

      <div class="canvas-wrapper" @dragover="onDragOver" @drop="onDrop" @mousemove="onMouseMove" @mouseup="onMouseUp">
        <div class="canvas" ref="canvas">
          <svg class="edges-svg">
            <defs>
              <marker id="arrowhead-lg" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                <polygon points="0 0, 10 3, 0 6" fill="#409eff" />
              </marker>
            </defs>
            <g v-for="edge in edges" :key="edge.id" @click="onEdgeClick(edge)">
              <path
                :d="getEdgePath(edge)"
                class="workflow-edge"
                :class="{ 'selected': selectedEdge?.id === edge.id }"
                marker-end="url(#arrowhead-lg)"
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
              <div class="node-content">
                <span class="node-label">{{ node.data.label }}</span>
                <span v-if="node.data.description" class="node-desc">{{ node.data.description }}</span>
              </div>
            </div>
            <div class="connection-point output"
                 @mousedown.stop="onOutputPointMouseDown($event, node)">
            </div>
          </div>
        </div>
      </div>

      <div class="config-panel" v-if="selectedNode || selectedEdge">
        <template v-if="selectedNode">
          <div class="panel-header">节点配置</div>
          <el-form :model="selectedNode.data" label-width="80px" size="small">
            <el-form-item label="节点名称">
              <el-input v-model="selectedNode.data.label" />
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="selectedNode.data.description" type="textarea" :rows="2" />
            </el-form-item>

            <template v-if="selectedNode.type === 'agent'">
              <el-divider content-position="left">智能体配置</el-divider>
              <el-form-item label="选择智能体">
                <el-select v-model="selectedNode.data.agent_id" style="width: 100%">
                  <el-option v-for="agent in agents" :key="agent.id" :label="agent.name" :value="agent.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="提示词">
                <el-input v-model="selectedNode.data.prompt" type="textarea" :rows="4" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'llm'">
              <el-divider content-position="left">LLM 配置</el-divider>
              <el-form-item label="选择模型">
                <el-select v-model="selectedNode.data.model_id" style="width: 100%">
                  <el-option 
                    v-for="model in models" 
                    :key="model.id" 
                    :label="`${model.provider_name} - ${model.model_name}`" 
                    :value="model.id" 
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="温度">
                <el-slider v-model="selectedNode.data.temperature" :min="0" :max="2" :step="0.1" />
              </el-form-item>
              <el-form-item label="提示词">
                <el-input v-model="selectedNode.data.prompt" type="textarea" :rows="4" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'condition'">
              <el-divider content-position="left">条件配置</el-divider>
              <el-form-item label="条件表达式">
                <el-input v-model="selectedNode.data.condition" type="textarea" :rows="3" placeholder="例如: i < 10" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'loop'">
              <el-divider content-position="left">循环配置</el-divider>
              <el-form-item label="循环条件">
                <el-input v-model="selectedNode.data.loop_condition" type="textarea" :rows="2" placeholder="例如: i < 5" />
              </el-form-item>
              <el-form-item label="最大次数">
                <el-input-number v-model="selectedNode.data.loop_max" :min="1" :max="1000" />
              </el-form-item>
              <el-form-item label="循环变量">
                <el-input v-model="selectedNode.data.loop_variable" placeholder="例如: i" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'iteration'">
              <el-divider content-position="left">迭代配置</el-divider>
              <el-form-item label="迭代列表">
                <el-input v-model="selectedNode.data.iteration_list" placeholder="变量名或JSON数组" />
              </el-form-item>
              <el-form-item label="当前项变量">
                <el-input v-model="selectedNode.data.iteration_variable" placeholder="例如: item" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'http'">
              <el-divider content-position="left">HTTP 配置</el-divider>
              <el-form-item label="方法">
                <el-select v-model="selectedNode.data.method">
                  <el-option label="GET" value="GET" />
                  <el-option label="POST" value="POST" />
                  <el-option label="PUT" value="PUT" />
                  <el-option label="DELETE" value="DELETE" />
                </el-select>
              </el-form-item>
              <el-form-item label="URL">
                <el-input v-model="selectedNode.data.url" />
              </el-form-item>
              <el-form-item label="请求体">
                <el-input v-model="selectedNode.data.body" type="textarea" :rows="3" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'code'">
              <el-divider content-position="left">代码配置</el-divider>
              <el-form-item label="语言">
                <el-select v-model="selectedNode.data.language">
                  <el-option label="Python" value="python" />
                  <el-option label="JavaScript" value="javascript" />
                </el-select>
              </el-form-item>
              <el-form-item label="代码">
                <el-input v-model="selectedNode.data.code" type="textarea" :rows="8" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'template'">
              <el-divider content-position="left">模板转换配置</el-divider>
              <el-form-item label="模板内容">
                <el-input v-model="selectedNode.data.template" type="textarea" :rows="4" placeholder="使用 {{变量名}} 引用变量" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_var" placeholder="例如: template_output" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'variable_aggregator'">
              <el-divider content-position="left">变量聚合器配置</el-divider>
              <el-form-item label="输入变量">
                <el-input v-model="selectedNode.data.input_vars" type="textarea" :rows="3" placeholder="每行一个变量名" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_var" placeholder="例如: aggregated_output" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'document_extractor'">
              <el-divider content-position="left">文档提取配置</el-divider>
              <el-form-item label="文档变量">
                <el-input v-model="selectedNode.data.document_var" placeholder="存储文档的变量名" />
              </el-form-item>
              <el-form-item label="提取规则">
                <el-input v-model="selectedNode.data.extract_rules" type="textarea" :rows="3" placeholder="提取规则" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_var" placeholder="例如: extracted_content" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'variable_assigner'">
              <el-divider content-position="left">变量赋值配置</el-divider>
              <el-form-item label="变量名">
                <el-input v-model="selectedNode.data.var_name" placeholder="要赋值的变量名" />
              </el-form-item>
              <el-form-item label="变量值">
                <el-input v-model="selectedNode.data.var_value" type="textarea" :rows="3" placeholder="变量值（支持 {{变量名}}）" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_var" placeholder="例如: assigned_var" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'parameter_extractor'">
              <el-divider content-position="left">参数提取配置</el-divider>
              <el-form-item label="输入文本变量">
                <el-input v-model="selectedNode.data.input_text" placeholder="存储输入文本的变量名" />
              </el-form-item>
              <el-form-item label="要提取的参数">
                <el-input v-model="selectedNode.data.parameters" type="textarea" :rows="3" placeholder="每行一个参数名" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_var" placeholder="例如: extracted_params" />
              </el-form-item>
            </template>
          </el-form>

          <el-button type="danger" size="small" @click="deleteSelectedNode" style="width: 100%; margin-top: 10px">
            删除节点
          </el-button>
        </template>

        <template v-if="selectedEdge">
          <div class="panel-header">连线配置</div>
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

    <el-dialog v-model="executeDialog" title="执行工作流" width="500px">
      <el-form label-width="100px">
        <el-form-item label="输入数据">
          <el-input v-model="executeInput" type="textarea" :rows="4" placeholder='{"text": "hello"}' />
        </el-form-item>
        <el-form-item label="执行结果" v-if="executeResult">
          <el-input :model-value="JSON.stringify(executeResult, null, 2)" type="textarea" :rows="6" readonly />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="executeDialog = false">关闭</el-button>
        <el-button type="primary" @click="doExecute" :loading="executing">执行</el-button>
      </template>
    </el-dialog>

    <input 
      ref="fileInput" 
      type="file" 
      accept=".json" 
      style="display: none"
      @change="handleFileImport"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { Check, VideoPlay, Download, Upload, User, Tools, Document, Link, Cpu, Filter, CircleCheck, VideoPlay as Play, Refresh, List, Collection, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAgents, getSkills, updateWorkflow, executeWorkflow as apiExecuteWorkflow } from '@/api/agent'
import { getModelList } from '@/api/llm'

const props = defineProps({
  workflowId: { type: [String, Number], default: null },
  title: { type: String, default: '' },
  initialNodes: { type: Array, default: () => [] },
  initialEdges: { type: Array, default: () => [] }
})

const emit = defineEmits(['save', 'execute', 'update:nodes', 'update:edges'])

const canvas = ref(null)
const fileInput = ref(null)

const saving = ref(false)
const executing = ref(false)
const executeDialog = ref(false)
const executeInput = ref('{}')
const executeResult = ref(null)

const agents = ref([])
const skills = ref([])
const models = ref([])

const nodes = ref([])
const edges = ref([])
const selectedNode = ref(null)
const selectedEdge = ref(null)

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

const nodeCategories = [
  {
    name: '基础节点',
    nodes: [
      { type: 'start', label: '开始', icon: Play },
      { type: 'end', label: '结束', icon: CircleCheck },
      { type: 'input', label: '输入', icon: Document },
      { type: 'output', label: '输出', icon: Document }
    ]
  },
  {
    name: 'AI 节点',
    nodes: [
      { type: 'agent', label: '智能体', icon: User },
      { type: 'llm', label: '大模型', icon: Cpu },
      { type: 'skill', label: '技能', icon: Tools }
    ]
  },
  {
    name: '控制流',
    nodes: [
      { type: 'condition', label: '条件判断', icon: Filter },
      { type: 'loop', label: '循环', icon: Refresh },
      { type: 'iteration', label: '迭代', icon: List },
      { type: 'parallel', label: '并行', icon: Link }
    ]
  },
  {
    name: '工具节点',
    nodes: [
      { type: 'http', label: 'HTTP 请求', icon: Link },
      { type: 'code', label: '代码执行', icon: Cpu }
    ]
  },
  {
    name: '数据处理',
    nodes: [
      { type: 'template', label: '模板转换', icon: Document },
      { type: 'variable_aggregator', label: '变量聚合器', icon: Collection },
      { type: 'document_extractor', label: '文档提取', icon: Document },
      { type: 'variable_assigner', label: '变量赋值', icon: Edit },
      { type: 'parameter_extractor', label: '参数提取', icon: Filter }
    ]
  }
]

const getNodeIcon = (type) => {
  const icons = {
    start: '▶️',
    end: '⏹️',
    input: '📥',
    output: '📤',
    agent: '🤖',
    llm: '🧠',
    skill: '⚡',
    condition: '🔀',
    loop: '🔄',
    iteration: '🔁',
    parallel: '🔗',
    http: '🌐',
    code: '💻',
    template: '📄',
    variable_aggregator: '📊',
    document_extractor: '📄',
    variable_assigner: '📝',
    parameter_extractor: '🔍'
  }
  return icons[type] || '📦'
}

const getNodeById = (id) => nodes.value.find(n => n.id === id)

const getEdgePath = (edge) => {
  const sourceNode = getNodeById(edge.source)
  const targetNode = getNodeById(edge.target)
  
  if (!sourceNode || !targetNode) return ''
  
  const sourceX = sourceNode.position.x + 180
  const sourceY = sourceNode.position.y + 30
  const targetX = targetNode.position.x
  const targetY = targetNode.position.y + 30
  
  const midX = (sourceX + targetX) / 2
  
  return `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`
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
  
  const canvasEl = event.currentTarget
  const rect = canvasEl.getBoundingClientRect()
  const position = {
    x: event.clientX - rect.left + canvasEl.scrollLeft - 75,
    y: event.clientY - rect.top + canvasEl.scrollTop - 25
  }
  
  const nodeData = {
    label: type,
    description: ''
  }
  
  if (type === 'loop') {
    nodeData.loop_condition = 'i < 5'
    nodeData.loop_max = 10
    nodeData.loop_variable = 'i'
  } else if (type === 'iteration') {
    nodeData.iteration_list = ''
    nodeData.iteration_variable = 'item'
  }
  
  const newNode = {
    id: `${type}-${Date.now()}`,
    type,
    position,
    data: nodeData
  }
  
  nodes.value.push(newNode)
}

const onNodeClick = (node) => {
  selectedEdge.value = null
  selectedNode.value = node
}

const onNodeMouseDown = (event, node) => {
  if (event.target.classList.contains('connection-point')) return
  
  draggingNode.value = node
  const canvasEl = canvas.value
  const rect = canvasEl.getBoundingClientRect()
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
    x: node.position.x + 180,
    y: node.position.y + 30
  }
  currentMousePos.value = { ...edgeStartPoint.value }
}

const onInputPointMouseDown = (event, node) => {
  event.stopPropagation()
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
    const canvasEl = canvas.value
    const rect = canvasEl.getBoundingClientRect()
    currentMousePos.value = {
      x: event.clientX - rect.left + canvasEl.scrollLeft,
      y: event.clientY - rect.top + canvasEl.scrollTop
    }
  }
  
  if (draggingNode.value) {
    const canvasEl = canvas.value
    const rect = canvasEl.getBoundingClientRect()
    draggingNode.value.position = {
      x: event.clientX - rect.left + canvasEl.scrollLeft - dragOffset.value.x,
      y: event.clientY - rect.top + canvasEl.scrollTop - dragOffset.value.y
    }
  }
}

const onMouseUp = () => {
  drawingEdge.value = false
  edgeStartNode.value = null
  draggingNode.value = null
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

const saveWorkflow = async () => {
  console.log('=== saveWorkflow 函数被调用 ===')
  console.log('props.workflowId:', props.workflowId)
  console.log('当前节点数:', nodes.value.length)
  console.log('当前边数:', edges.value.length)
  
  if (props.workflowId) {
    saving.value = true
    try {
      const definition = {
        nodes: JSON.parse(JSON.stringify(nodes.value)),
        edges: JSON.parse(JSON.stringify(edges.value))
      }
      
      console.log('准备保存工作流，definition:', definition)
      await updateWorkflow(props.workflowId, {
        definition
      })
      ElMessage.success('保存成功')
    } catch (error) {
      console.error('保存工作流失败:', error)
      ElMessage.error('保存失败: ' + (error.message || error))
    } finally {
      saving.value = false
    }
  }
  console.log('LangGraphEditor 发出 save 事件:', { nodes: nodes.value, edges: edges.value })
  emit('save', { 
    nodes: JSON.parse(JSON.stringify(nodes.value)), 
    edges: JSON.parse(JSON.stringify(edges.value)) 
  })
}

const executeWorkflowDialog = () => {
  executeDialog.value = true
  executeInput.value = '{}'
  executeResult.value = null
}

const doExecute = async () => {
  if (!props.workflowId) {
    ElMessage.warning('请先创建工作流')
    return
  }

  executing.value = true
  try {
    const input = JSON.parse(executeInput.value)
    const res = await apiExecuteWorkflow(props.workflowId, input)
    executeResult.value = res.data
    ElMessage.success('执行成功')
    emit('execute', res.data)
  } catch (error) {
    ElMessage.error('执行失败')
  } finally {
    executing.value = false
  }
}

const exportWorkflow = () => {
  const data = {
    nodes: nodes.value,
    edges: edges.value
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'workflow.json'
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

const importWorkflow = () => {
  fileInput.value.click()
}

const handleFileImport = (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result)
      if (data.nodes) nodes.value = data.nodes
      if (data.edges) edges.value = data.edges
      ElMessage.success('导入成功')
    } catch (err) {
      ElMessage.error('文件格式错误')
    }
  }
  reader.readAsText(file)
  event.target.value = ''
}

const fetchAgents = async () => {
  try {
    const res = await getAgents({ limit: 1000 })
    agents.value = res.data?.items || res.data || []
  } catch (error) {
    console.error(error)
  }
}

const fetchSkills = async () => {
  try {
    const res = await getSkills({ limit: 1000 })
    skills.value = res.data?.items || res.data || []
  } catch (error) {
    console.error(error)
  }
}

const fetchModels = async () => {
  try {
    const res = await getModelList({ limit: 1000 })
    models.value = res.data?.items || res.data || []
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  fetchAgents()
  fetchSkills()
  fetchModels()
  
  console.log('=== LangGraphEditor onMounted ===')
  console.log('props.initialNodes:', props.initialNodes)
  console.log('props.initialEdges:', props.initialEdges)
  
  if (props.initialNodes.length > 0) {
    console.log('初始化 nodes.value:', props.initialNodes)
    nodes.value = props.initialNodes
  }
  if (props.initialEdges.length > 0) {
    console.log('初始化 edges.value:', props.initialEdges)
    edges.value = props.initialEdges
  }
})

// 监听 initialNodes 变化
watch(() => props.initialNodes, (newNodes) => {
  console.log('=== watch initialNodes 变化 ===')
  console.log('newNodes:', newNodes)
  console.log('newNodes.length:', newNodes.length)
  
  if (newNodes.length > 0) {
    nodes.value = JSON.parse(JSON.stringify(newNodes))
    console.log('已更新 nodes.value:', nodes.value)
  }
}, { immediate: true, deep: true })

// 监听 initialEdges 变化
watch(() => props.initialEdges, (newEdges) => {
  console.log('=== watch initialEdges 变化 ===')
  console.log('newEdges:', newEdges)
  console.log('newEdges.length:', newEdges.length)
  
  if (newEdges.length > 0) {
    edges.value = JSON.parse(JSON.stringify(newEdges))
    console.log('已更新 edges.value:', edges.value)
  }
}, { immediate: true, deep: true })
</script>

<style scoped>
.langgraph-editor {
  height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.toolbar {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  gap: 12px;
}

.title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.toolbar-right {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.editor-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.node-sidebar {
  width: 240px;
  background: white;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.sidebar-header {
  padding: 16px;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid #e4e7ed;
}

.node-category {
  padding: 0 12px;
}

.category-title {
  padding: 12px 4px 8px;
  font-size: 12px;
  color: #909399;
  font-weight: 500;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 6px;
  cursor: grab;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.node-item:hover {
  background: #ecf5ff;
  border-color: #409EFF;
}

.help-section {
  margin-top: auto;
  border-top: 1px solid #e4e7ed;
}

.help-section ul {
  padding: 12px 16px 16px 32px;
  margin: 0;
  font-size: 12px;
  color: #606266;
  line-height: 2;
}

.canvas-wrapper {
  flex: 1;
  position: relative;
  overflow: auto;
}

.canvas {
  position: relative;
  min-width: 2000px;
  min-height: 1500px;
  width: 100%;
  height: 100%;
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
  padding: 12px 16px;
  background: white;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  min-width: 150px;
  cursor: move;
  transition: all 0.2s;
  user-select: none;
}

.workflow-node:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.workflow-node.selected {
  border-color: #409EFF;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.15);
}

.workflow-node.start-node {
  border-color: #67C23A;
  background: linear-gradient(135deg, #f0f9ff 0%, #e6fffa 100%);
}

.workflow-node.end-node {
  border-color: #F56C6C;
  background: linear-gradient(135deg, #fef0f0 0%, #fff0f0 100%);
}

.workflow-node.agent-node {
  border-color: #909399;
  background: linear-gradient(135deg, #f4f4f5 0%, #fafafa 100%);
}

.workflow-node.llm-node {
  border-color: #909399;
  background: linear-gradient(135deg, #f4f4f5 0%, #fafafa 100%);
}

.workflow-node.http-node {
  border-color: #409EFF;
  background: linear-gradient(135deg, #ecf5ff 0%, #f0f7ff 100%);
}

.workflow-node.code-node {
  border-color: #909399;
  background: linear-gradient(135deg, #f4f4f5 0%, #fafafa 100%);
}

.workflow-node.loop-node {
  border-color: #E6A23C;
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
}

.workflow-node.iteration-node {
  border-color: #909399;
  background: linear-gradient(135deg, #f4f4f5 0%, #fafafa 100%);
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.node-icon {
  font-size: 18px;
}

.node-label {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.node-desc {
  font-size: 11px;
  color: #909399;
}

.connection-point {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #409EFF;
  border: 2px solid #fff;
  border-radius: 50%;
  cursor: crosshair;
  transition: all 0.2s;
  z-index: 10;
}

.connection-point:hover {
  transform: scale(1.3);
  background: #67C23A;
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
  width: 320px;
  background: white;
  border-left: 1px solid #e4e7ed;
  padding: 16px;
  overflow-y: auto;
}

.panel-header {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.edge-info {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 16px;
}

.edge-info p {
  margin: 6px 0;
  font-size: 13px;
}
</style>
