<template>
  <div class="langgraph-editor">
    <div class="toolbar">
      <span class="title">{{ title || 'LangGraph 工程图编辑器' }}</span>
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
              <el-form-item label="最大Token">
                <el-input-number v-model="selectedNode.data.max_tokens" :min="1" :max="4096" />
              </el-form-item>
              <el-form-item label="提示词">
                <el-input v-model="selectedNode.data.prompt" type="textarea" :rows="4" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_var" placeholder="例如: llm_output" />
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
            
            <template v-if="selectedNode.type === 'output'">
              <el-divider content-position="left">输出配置</el-divider>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_var" placeholder="例如: final_output" />
              </el-form-item>
              <el-form-item label="输出内容">
                <el-input v-model="selectedNode.data.output_content" type="textarea" :rows="3" placeholder="可选，输出内容模板（支持 {{变量名}}）" />
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
              <el-form-item label="输入变量">
                <el-input v-model="selectedNode.data.input_variable" placeholder="要提取的变量名" />
              </el-form-item>
              <el-form-item label="要提取的参数">
                <el-input v-model="selectedNode.data.parameters" type="textarea" :rows="3" placeholder="每行一个参数名" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_var" placeholder="例如: extracted_params" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'json_extractor'">
              <el-divider content-position="left">JSON提取配置</el-divider>
              <el-form-item label="输入变量">
                <el-input v-model="selectedNode.data.input_variable" placeholder="包含JSON的变量名（如: llm_output, thinking_process）" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_variable" placeholder="例如: task_plan, structured_output" />
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="selectedNode.data.description" type="textarea" :rows="2" placeholder="节点描述（可选）" />
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

    <el-dialog v-model="executeDialog" title="执行工程图" width="900px" class="wechat-style-dialog">
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

        <!-- 实时执行步骤 -->
        <div class="realtime-steps" v-if="executing || realtimeSteps.length > 0">
          <div class="steps-header">执行步骤</div>
          <div
            v-for="(step, index) in realtimeSteps"
            :key="index"
            :class="['step-item', step.type]"
          >
            <div class="step-icon">{{ getStepIcon(step.type) }}</div>
            <div class="step-content">
              <div class="step-label">{{ step.title }}</div>
              <div class="step-description">{{ step.content }}</div>
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
            <el-button @click="abortExecution" :disabled="!executing">中断</el-button>
            <el-button type="primary" @click="doExecute" :loading="executing">发送</el-button>
          </div>
        </div>
      </div>
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
import { getAgents, getSkills, updateWorkflow, executeWorkflow as apiExecuteWorkflow, executeAgentGraph } from '@/api/agent'
import { getModelList } from '@/api/llm'

const props = defineProps({
  workflowId: { type: [String, Number], default: null },
  agentId: { type: [String, Number], default: null },
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
const activeTab = ref('full')
const realtimeSteps = ref([]) // 实时执行步骤
const dialogHistory = ref([]) // 对话历史
const currentInput = ref('') // 当前输入
const latestResponse = ref('') // 最新回复

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
  
  const startX = edgeStartPoint.value.x
  const startY = edgeStartPoint.value.y
  const endX = currentMousePos.value.x
  const endY = currentMousePos.value.y
  
  // 使用平滑的曲线绘制临时连线
  const dx = endX - startX
  const curvature = Math.min(Math.abs(dx) * 0.3, 80)
  
  const cp1x = startX + curvature
  const cp1y = startY
  const cp2x = endX - curvature
  const cp2y = endY
  
  return `M ${startX} ${startY} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${endX} ${endY}`
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
      { type: 'parameter_extractor', label: '参数提取', icon: Filter },
      { type: 'json_extractor', label: 'JSON提取', icon: Collection }
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
    parameter_extractor: '🔍',
    json_extractor: '📋'
  }
  return icons[type] || '📦'
}

const getTraceStepType = (type) => {
  const types = {
    start: 'success',
    end: 'success',
    llm: 'primary',
    agent: 'info',
    skill: 'warning',
    condition: 'danger',
    loop: 'info',
    default: ''
  }
  return types[type] || ''
}

const hasTaskPlan = computed(() => {
  const vars = executeResult.value?.variables
  return vars && (vars.original_task || vars.subtasks || vars.task_plan || vars.plan)
})

const getSubtaskColor = (index) => {
  const colors = ['', 'primary', 'success', 'warning', 'info', 'danger']
  return colors[index % colors.length]
}

const formatContent = (content) => {
  if (!content) return ''
  
  // 如果内容包含HTML标签，直接返回以使用v-html渲染
  if (content.includes('<') && content.includes('>')) {
    return content
  }
  
  // 否则，处理换行等格式
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
    .replace(/\s{4}/g, '&nbsp;&nbsp;&nbsp;&nbsp;')
}

const getNodeById = (id) => nodes.value.find(n => n.id === id)

// 实时执行步骤相关函数
const getStepType = (type) => {
  const typeMap = {
    think: 'primary',
    act: 'success',
    observe: 'warning',
    info: 'info',
    error: 'danger'
  }
  return typeMap[type] || ''
}

const getStepLabel = (type) => {
  const labelMap = {
    think: '🧠 思考',
    act: '⚡ 行动',
    observe: '👁️ 观察',
    info: '📋 信息',
    error: '❌ 错误'
  }
  return labelMap[type] || type
}

const addRealtimeStep = (type, title, content) => {
  realtimeSteps.value.push({
    type,
    title,
    content,
    completed: false,
    timestamp: new Date().toLocaleTimeString('zh-CN')
  })
}

const markLastStepCompleted = () => {
  if (realtimeSteps.value.length > 0) {
    realtimeSteps.value[realtimeSteps.value.length - 1].completed = true
  }
}

const getEdgePath = (edge) => {
  const sourceNode = getNodeById(edge.source)
  const targetNode = getNodeById(edge.target)
  
  if (!sourceNode || !targetNode) return ''
  
  const sourceX = sourceNode.position.x + 180
  const sourceY = sourceNode.position.y + 30
  const targetX = targetNode.position.x
  const targetY = targetNode.position.y + 30
  
  // 计算同一源节点的连线索引，用于偏移
  const sourceEdges = edges.value.filter(e => e.source === edge.source)
  const edgeIndex = sourceEdges.findIndex(e => e.id === edge.id)
  const totalEdgesFromSource = sourceEdges.length
  
  // 计算垂直偏移量，避免重叠
  let yOffset = 0
  if (totalEdgesFromSource > 1) {
    // 计算每条连线的偏移位置
    const spacing = 25 // 连线之间的间距
    const totalHeight = (totalEdgesFromSource - 1) * spacing
    const startOffset = -totalHeight / 2
    yOffset = startOffset + edgeIndex * spacing
  }
  
  // 计算控制点
  const dx = targetX - sourceX
  const dy = targetY - sourceY
  const distance = Math.sqrt(dx * dx + dy * dy)
  
  // 根据距离调整控制点，使曲线更自然
  const curvature = Math.min(distance * 0.3, 100)
  
  // 计算控制点，考虑垂直偏移
  const cp1x = sourceX + curvature
  const cp1y = sourceY + yOffset
  const cp2x = targetX - curvature
  const cp2y = targetY + yOffset
  
  return `M ${sourceX} ${sourceY} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${targetX} ${targetY}`
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
      
      console.log('准备保存工程图，definition:', definition)
      await updateWorkflow(props.workflowId, {
        definition
      })
      ElMessage.success('保存成功')
    } catch (error) {
      console.error('保存工程图失败:', error)
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

// 监听对话框打开，清空步骤
watch(() => executeDialog.value, (newVal) => {
  if (newVal) {
    realtimeSteps.value = [] // 打开时清空之前的步骤
    executeResult.value = null
    currentInput.value = ''
    latestResponse.value = ''
  }
})

const clearDialogHistory = () => {
  dialogHistory.value = []
  currentInput.value = ''
  latestResponse.value = ''
  realtimeSteps.value = []
  executeResult.value = null
  ElMessage.success('对话历史已清空')
}

// 获取步骤图标
const getStepIcon = (type) => {
  const iconMap = {
    info: 'ℹ️',
    error: '❌',
    success: '✅',
    warning: '⚠️',
    think: '🤔',
    act: '⚡',
    observe: '👁️',
    thinking: '🤔',
    action: '⚡',
    result: '📋'
  }
  return iconMap[type] || 'ℹ️'
}

const doExecute = async () => {
  console.log('=== doExecute 函数被调用 ===')
  console.log('props.workflowId:', props.workflowId)
  console.log('props.agentId:', props.agentId)
  
  if (!props.workflowId && !props.agentId) {
    ElMessage.warning('请先创建工程图或智能体')
    return
  }
  
  if (!currentInput.value.trim()) {
    ElMessage.warning('请输入内容')
    return
  }
  
  realtimeSteps.value = [] // 清空旧步骤
  executing.value = true
  
  try {
    console.log('开始执行，currentInput.value:', currentInput.value)
    
    // 添加用户输入到历史
    const userMessage = {
      role: 'user',
      content: currentInput.value,
      time: new Date().toLocaleTimeString('zh-CN')
    }
    dialogHistory.value.push(userMessage)
    
    addRealtimeStep('info', '开始执行', `输入文本: ${currentInput.value.trim().substring(0, 100)}...`)
    markLastStepCompleted()
    
    // 将普通文本转换为JSON格式，包含对话历史
    const input = {
      text: currentInput.value.trim(),
      history: [...dialogHistory.value]
    }
    console.log('转换后的input:', input)
    
    let res
    
    if (props.agentId) {
      console.log('执行智能体结构图:', props.agentId, input)
      console.log('调用 executeAgentGraph 函数')
      
      addRealtimeStep('info', '准备执行', '正在调用智能体执行接口...')
      
      // 模拟实时步骤（实际项目中可以用WebSocket或SSE）
      addRealtimeStep('think', '分析问题', '正在分析用户需求...')
      await new Promise(resolve => setTimeout(resolve, 500))
      markLastStepCompleted()
      
      res = await executeAgentGraph(props.agentId, input)
      console.log('执行结果:', res)
      console.log('执行结果类型:', typeof res)
      console.log('执行结果结构:', Object.keys(res))
    } else {
      console.log('执行工程图:', props.workflowId, input)
      console.log('调用 apiExecuteWorkflow 函数')
      res = await apiExecuteWorkflow(props.workflowId, input)
      console.log('执行结果:', res)
      console.log('执行结果类型:', typeof res)
      console.log('执行结果结构:', Object.keys(res))
    }
    
    // 从执行结果中提取步骤并显示
    if (res.data) {
      const result = res.data
      
      // 处理思考过程
      if (result.variables) {
        // 处理推理
        if (result.variables.analysis_raw || result.variables.analysis_result) {
          addRealtimeStep('think', '推理 - 分析需求', 
            result.variables.analysis_raw?.response || JSON.stringify(result.variables.analysis_result, null, 2) || '需求分析完成')
          markLastStepCompleted()
        }
        
        // 处理行动
        if (result.variables.decompose_raw || result.variables.task_plan) {
          addRealtimeStep('act', '行动 - 任务分解', 
            result.variables.decompose_raw?.response || JSON.stringify(result.variables.task_plan, null, 2) || '任务分解完成')
          markLastStepCompleted()
        }
        
        // 处理观察
        if (result.variables.observe_raw || result.variables.observation_result) {
          addRealtimeStep('observe', '观察 - 评估结果', 
            result.variables.observe_raw?.response || JSON.stringify(result.variables.observation_result, null, 2) || '评估完成')
          markLastStepCompleted()
        }
        
        // 处理最终报告
        if (result.variables.final_report) {
          addRealtimeStep('info', '生成报告', '正在生成最终报告...')
          markLastStepCompleted()
        }
      }
      
      // 处理执行轨迹
      if (result.trace) {
        for (const step of result.trace) {
          if (step.node_type === 'llm') {
            const stepType = step.label?.includes('思考') || step.label?.includes('推理') ? 'think' : 
                            step.label?.includes('观察') || step.label?.includes('评估') ? 'observe' : 'act'
            addRealtimeStep(stepType, step.label || `执行节点: ${step.node_type}`, JSON.stringify(step, null, 2))
            markLastStepCompleted()
          }
        }
      }
    }
    
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
    
    // 构建process数组
    const process = []
    
    // 添加思考过程
    if (res.data.variables?.analysis_raw || res.data.variables?.analysis_result) {
      process.push({
        type: 'thinking',
        label: '思考',
        content: res.data.variables.analysis_raw?.response || JSON.stringify(res.data.variables.analysis_result, null, 2) || '需求分析完成',
        time: new Date().toLocaleTimeString('zh-CN'),
        collapsed: false
      })
    }
    
    // 添加行动过程
    if (res.data.variables?.decompose_raw || res.data.variables?.task_plan) {
      process.push({
        type: 'action',
        label: '行动',
        content: res.data.variables.decompose_raw?.response || JSON.stringify(res.data.variables.task_plan, null, 2) || '任务分解完成',
        time: new Date().toLocaleTimeString('zh-CN'),
        collapsed: false
      })
    }
    
    // 添加观察过程
    if (res.data.variables?.observe_raw || res.data.variables?.observation_result) {
      process.push({
        type: 'action',
        label: '观察',
        content: res.data.variables.observe_raw?.response || JSON.stringify(res.data.variables.observation_result, null, 2) || '评估完成',
        time: new Date().toLocaleTimeString('zh-CN'),
        collapsed: false
      })
    }
    
    // 添加结果
    process.push({
      type: 'result',
      label: '结果',
      content: assistantResponse,
      time: new Date().toLocaleTimeString('zh-CN'),
      collapsed: false
    })
    
    // 添加助手回复到历史
    const assistantMessage = {
      role: 'assistant',
      content: assistantResponse,
      time: new Date().toLocaleTimeString('zh-CN'),
      process: process
    }
    dialogHistory.value.push(assistantMessage)
    
    // 更新最新回复
    latestResponse.value = assistantResponse
    
    // 清空输入框
    currentInput.value = ''
    
    console.log('设置executeResult.value:', res.data)
    executeResult.value = res.data
    
    addRealtimeStep('info', '执行完成', '工程图执行完成，结果已生成')
    markLastStepCompleted()
    
    ElMessage.success('发送成功')
    emit('execute', res.data)
  } catch (error) {
    console.error('执行失败:', error)
    console.error('错误堆栈:', error.stack)
    console.error('错误类型:', typeof error)
    console.error('错误对象结构:', error)
    
    // 即使出错也要显示错误
    const errorMessage = {
      role: 'assistant',
      content: '执行失败: ' + (error.message || '未知错误'),
      time: new Date().toLocaleTimeString('zh-CN')
    }
    dialogHistory.value.push(errorMessage)
    latestResponse.value = errorMessage.content
    
    addRealtimeStep('error', '执行失败', error.message || '未知错误')
    markLastStepCompleted()
    
    ElMessage.error('执行失败: ' + (error.message || '未知错误'))
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

.task-plan-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-plan-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.subtask-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.subtask-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
  border-left: 3px solid #409EFF;
}

.subtask-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.subtask-index {
  min-width: 50px;
  text-align: center;
}

.subtask-name {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.subtask-description {
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
}

.subtask-meta {
  margin-top: 8px;
}

.llm-response {
  margin-bottom: 16px;
}

.response-meta {
  margin-bottom: 8px;
}

.trace-step {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.thinking-content-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.thinking-content {
  max-height: 400px;
  overflow-y: auto;
}

.thinking-content :deep(p) {
  margin: 8px 0;
  line-height: 1.8;
}

.thinking-content :deep(br) {
  line-height: 2;
}

.thinking-content :deep(ul),
.thinking-content :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.thinking-content :deep(li) {
  margin: 4px 0;
  line-height: 1.8;
}

.thinking-content :deep(code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: #409EFF;
}

.thinking-content :deep(pre) {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}

.thinking-content :deep(h1),
.thinking-content :deep(h2),
.thinking-content :deep(h3),
.thinking-content :deep(h4) {
  margin: 12px 0 8px 0;
  color: #303133;
}

.thinking-content :deep(blockquote) {
  border-left: 4px solid #409EFF;
  padding-left: 12px;
  margin: 8px 0;
  color: #606266;
}

.response-content {
  max-height: 300px;
  overflow-y: auto;
}

.response-content :deep(p) {
  margin: 8px 0;
  line-height: 1.8;
}

.response-content :deep(br) {
  line-height: 2;
}

.response-content :deep(ul),
.response-content :deep(ol) {
  margin: 8px 0;
}

/* 实时执行样式 */
.realtime-execution-container {
  max-height: 500px;
  overflow-y: auto;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
}

.realtime-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  margin-bottom: 10px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  transition: all 0.3s;
}

.realtime-step:hover {
  border-color: #409EFF;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.step-type-tag {
  flex-shrink: 0;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin-bottom: 6px;
}

.step-description {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.step-check-icon {
  flex-shrink: 0;
  color: #67C23A;
  font-size: 18px;
  margin-top: 2px;
}

.executing-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  color: #909399;
  font-size: 14px;
}

.loading-icon {
  animation: rotate 1s linear infinite;
  color: #409EFF;
  font-size: 20px;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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

.response-content :deep(li) {
  margin: 4px 0;
  line-height: 1.8;
}

.response-content :deep(code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: #409EFF;
}

.response-content :deep(pre) {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}

.response-content :deep(h1),
.response-content :deep(h2),
.response-content :deep(h3),
.response-content :deep(h4) {
  margin: 12px 0 8px 0;
  color: #303133;
}

.response-content :deep(blockquote) {
  border-left: 4px solid #409EFF;
  padding-left: 12px;
  margin: 8px 0;
  color: #606266;
}

.response-content-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-top: 8px;
}

.response-content-card pre {
  margin: 0;
  padding: 0;
  font-family: 'Microsoft YaHei', sans-serif;
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
  word-wrap: break-word;
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

/* 实时步骤 */
.realtime-steps {
  max-height: 150px;
  overflow-y: auto;
  padding: 10px 20px;
  background: #fdf6ec;
  border-top: 1px solid #e4e7ed;
  border-bottom: 1px solid #e4e7ed;
}

.steps-header {
  font-size: 12px;
  font-weight: 600;
  color: #e6a23c;
  margin-bottom: 8px;
}

.step-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 6px;
  padding: 6px;
  background: #fff;
  border-radius: 4px;
  font-size: 12px;
}

.step-icon {
  font-size: 16px;
  margin-right: 8px;
  flex-shrink: 0;
  margin-top: 1px;
}

.step-content {
  flex: 1;
}

.step-label {
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}

.step-description {
  color: #606266;
  line-height: 1.4;
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
