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
            <li>滚轮缩放画布</li>
          </ul>
        </div>
      </div>

      <div 
        class="canvas-wrapper" 
        @dragover="onDragOver" 
        @drop="onDrop" 
        @mousemove="onMouseMove" 
        @mouseup="onMouseUp"
        @wheel.prevent="onWheel"
      >
        <div 
          class="canvas" 
          ref="canvas"
          :style="canvasStyle"
        >
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
            :style="getNodeStyle(node)"
          >
            <div class="connection-point input" 
                 @mousedown.stop="onInputPointMouseDown($event, node)"
                 @mouseup="onInputPointMouseUp($event, node)"
            >
            </div>
            <div class="node-header">
              <span class="node-icon">{{ getNodeIcon(node.type) }}</span>
              <div class="node-content">
                <span class="node-label">{{ node.data.label }}</span>
                <span v-if="node.data.description" class="node-desc">{{ node.data.description }}</span>
              </div>
            </div>
            <div class="connection-point output"
                 @mousedown.stop="onOutputPointMouseDown($event, node)"
            >
            </div>
          </div>
        </div>
      </div>

      <div class="canvas-zoom-controls">
        <el-button 
          :icon="ZoomIn" 
          @click="zoomIn" 
          :disabled="zoom >= MAX_ZOOM"
          size="small"
          circle
          title="放大"
        />
        <div class="canvas-zoom-value">{{ Math.round(zoom * 100) }}%</div>
        <el-button 
          :icon="ZoomOut" 
          @click="zoomOut" 
          :disabled="zoom <= MIN_ZOOM"
          size="small"
          circle
          title="缩小"
        />
        <el-button 
          :icon="Refresh" 
          @click="resetZoom" 
          size="small"
          circle
          title="重置"
        />
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

            <template v-if="selectedNode.type === 'llm'">
              <el-divider content-position="left">LLM 配置</el-divider>
              <el-form-item label="选择模型">
                <el-select v-model="selectedNode.data.modelId" style="width: 100%">
                  <el-option 
                    v-for="model in models" 
                    :key="model.id" 
                    :label="`${model.provider_name} - ${model.model_name}`" 
                    :value="model.id" 
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="选择技能">
                <el-select 
                  v-model="selectedNode.data.skillIds" 
                  multiple 
                  style="width: 100%" 
                  placeholder="选择技能"
                >
                  <el-option 
                    v-for="skill in skills" 
                    :key="skill.id" 
                    :label="skill.name" 
                    :value="skill.id" 
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="温度">
                <el-slider v-model="selectedNode.data.temperature" :min="0" :max="2" :step="0.1" />
              </el-form-item>
              <el-form-item label="最大Token">
                <el-input-number v-model="selectedNode.data.maxTokens" :min="1" :max="4096" />
              </el-form-item>
              <el-form-item label="流式输出">
                <el-switch v-model="selectedNode.data.stream" active-text="开" inactive-text="关" />
              </el-form-item>
              <el-form-item label="提示词">
                <el-input v-model="selectedNode.data.prompt" type="textarea" :rows="4" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.outputVar" placeholder="例如: llm_output" />
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
                <el-input v-model="selectedNode.data.condition" type="textarea" :rows="2" placeholder="例如: i < 5" />
              </el-form-item>
              <el-form-item label="最大次数">
                <el-input-number v-model="selectedNode.data.loopMax" :min="1" :max="1000" />
              </el-form-item>
              <el-form-item label="循环变量">
                <el-input v-model="selectedNode.data.loopVariable" placeholder="例如: i" />
              </el-form-item>
            </template>

            <template v-if="selectedNode.type === 'iteration'">
              <el-divider content-position="left">迭代配置</el-divider>
              <el-form-item label="迭代列表">
                <el-input v-model="selectedNode.data.iterationList" placeholder="变量名或JSON数组" />
              </el-form-item>
              <el-form-item label="当前项变量">
                <el-input v-model="selectedNode.data.iterationVariable" placeholder="例如: item" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'output'">
              <el-divider content-position="left">输出配置</el-divider>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.outputVar" placeholder="例如: final_output" />
              </el-form-item>
              <el-form-item label="输出内容">
                <el-input v-model="selectedNode.data.outputContent" type="textarea" :rows="3" placeholder="可选，输出内容模板（支持 {{变量名}}）" />
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
                <el-input v-model="selectedNode.data.outputVar" placeholder="例如: template_output" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'variable_aggregator'">
              <el-divider content-position="left">变量聚合器配置</el-divider>
              <el-form-item label="输入变量">
                <el-input v-model="selectedNode.data.inputVars" type="textarea" :rows="3" placeholder="每行一个变量名" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.outputVar" placeholder="例如: aggregated_output" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'document_extractor'">
              <el-divider content-position="left">文档提取配置</el-divider>
              <el-form-item label="文档变量">
                <el-input v-model="selectedNode.data.documentVar" placeholder="存储文档的变量名" />
              </el-form-item>
              <el-form-item label="提取规则">
                <el-input v-model="selectedNode.data.extractRules" type="textarea" :rows="3" placeholder="提取规则" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.outputVar" placeholder="例如: extracted_content" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'variable_assigner'">
              <el-divider content-position="left">变量赋值配置</el-divider>
              <el-form-item label="变量名">
                <el-input v-model="selectedNode.data.varName" placeholder="要赋值的变量名" />
              </el-form-item>
              <el-form-item label="变量值">
                <el-input v-model="selectedNode.data.varValue" type="textarea" :rows="3" placeholder="变量值（支持 {{变量名}}）" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.outputVar" placeholder="例如: assigned_var" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'parameter_extractor'">
              <el-divider content-position="left">参数提取配置</el-divider>
              <el-form-item label="输入变量">
                <el-input v-model="selectedNode.data.inputVariable" placeholder="要提取的变量名" />
              </el-form-item>
              <el-form-item label="要提取的参数">
                <el-input v-model="selectedNode.data.parameters" type="textarea" :rows="3" placeholder="每行一个参数名" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.outputVar" placeholder="例如: extracted_params" />
              </el-form-item>
            </template>
            
            <template v-if="selectedNode.type === 'json_extractor'">
              <el-divider content-position="left">JSON提取配置</el-divider>
              <el-form-item label="输入变量">
                <el-input v-model="selectedNode.data.inputVariable" placeholder="包含JSON的变量名（如: llm_output, thinking_process）" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.outputVariable" placeholder="例如: task_plan, structured_output" />
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
        <div class="chat-messages">
          <div
            v-for="(msg, index) in dialogHistory"
            :key="index"
            :class="['message', msg.role, { 'message-streaming': msg.role === 'assistant' && index === dialogHistory.length - 1 && executing }]"
          >
            <div class="message-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
            <div class="message-content-wrapper">
              <div class="message-role">{{ msg.role === 'user' ? '用户' : 'AI' }}</div>
              <div class="message-content">
                {{ msg.content }}
                <span v-if="msg.role === 'assistant'" class="typing-dots" v-show="index === dialogHistory.length - 1 && executing">{{ typingDots }}</span>
              </div>
              <div class="message-time">{{ msg.time }}</div>
            </div>
          </div>
        </div>

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
import { Check, VideoPlay, Download, Upload, User, Tools, Document, Link, Cpu, Filter, CircleCheck, VideoPlay as Play, Refresh, List, Collection, Edit, ZoomIn, ZoomOut } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAgents, getSkills, updateWorkflow, executeWorkflow as apiExecuteWorkflow, executeAgentGraphAuto } from '@/api/agent'
import { getModelList } from '@/api/llm'
import { getEdgePathByType, getDefaultEdgeType } from '@/utils/edge-renderer';

const safeConsole = {
  log: function() {},
  error: function() {},
  warn: function() {}
};

try {
  if (typeof console !== 'undefined') {
    if (typeof console.log === 'function') {
      safeConsole.log = console.log.bind(console);
    }
    if (typeof console.error === 'function') {
      safeConsole.error = console.error.bind(console);
    }
    if (typeof console.warn === 'function') {
      safeConsole.warn = console.warn.bind(console);
    }
  }
} catch (e) {}

const props = defineProps({
  workflowId: { type: [String, Number], default: null },
  agentId: { type: [String, Number], default: null },
  title: { type: String, default: '' },
  initialNodes: { type: Array, default: () => [] },
  initialEdges: { type: Array, default: () => [] }
});

const emit = defineEmits(['save', 'execute', 'update:nodes', 'update:edges']);

const canvas = ref(null);
const fileInput = ref(null);

const saving = ref(false);
const executing = ref(false);
const executeDialog = ref(false);
const executeInput = ref('{}');
const executeResult = ref(null);
const activeTab = ref('full');
const realtimeSteps = ref([]);
const dialogHistory = ref([]);
const currentInput = ref('');
const latestResponse = ref('');
const currentProcess = ref([]);
const assistantMessage = ref(null);
const currentAbortController = ref(null);

const typingDots = ref('');
let typingInterval = null;

const agents = ref([]);
const skills = ref([]);
const models = ref([]);

const nodes = ref([]);
const edges = ref([]);
const selectedNode = ref(null);
const selectedEdge = ref(null);

const zoom = ref(1);
const MIN_ZOOM = 0.2;
const MAX_ZOOM = 3;
const ZOOM_STEP = 0.1;

const edgeType = getDefaultEdgeType();

const drawingEdge = ref(false);
const edgeStartNode = ref(null);
const edgeStartPoint = ref({ x: 0, y: 0 });
const currentMousePos = ref({ x: 0, y: 0 });
const draggingNode = ref(null);
const dragOffset = ref({ x: 0, y: 0 });

const canvasStyle = computed(() => {
  return {
    transform: `scale(${zoom.value})`,
    transformOrigin: 'top left'
  };
});

const tempEdgePath = computed(() => {
  if (!drawingEdge.value) return '';
  
  const startX = edgeStartPoint.value.x;
  const startY = edgeStartPoint.value.y;
  const endX = currentMousePos.value.x;
  const endY = currentMousePos.value.y;
  
  return getEdgePathByType(edgeType, startX, startY, endX, endY, 0);
});

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
      { type: 'llm', label: '大模型', icon: Cpu }
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
];

const nodeTypes = nodeCategories.flatMap(category => category.nodes);

const getNodeIcon = (type) => {
  const icons = {
    start: '▶️',
    end: '⏹️',
    input: '📥',
    output: '📤',
    agent: '🤖',
    llm: '🧠',
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
  };
  return icons[type] || '📦';
};

const getNodeStyle = (node) => {
  return {
    left: node.position.x + 'px',
    top: node.position.y + 'px'
  };
};

const getTraceStepType = (type) => {
  const types = {
    start: 'success',
    end: 'success',
    llm: 'primary',
    agent: 'info',
    condition: 'danger',
    loop: 'info',
    default: ''
  };
  return types[type] || '';
};

const formatContent = (content) => {
  if (!content) return '';
  
  if (content.includes('<') && content.includes('>')) {
    return content;
  }
  
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
    .replace(/\s{4}/g, '&nbsp;&nbsp;&nbsp;&nbsp;');
};

const getNodeById = (id) => nodes.value.find(n => n.id === id);

const getStepType = (type) => {
  const typeMap = {
    think: 'primary',
    act: 'success',
    observe: 'warning',
    info: 'info',
    error: 'danger'
  };
  return typeMap[type] || '';
};

const getStepLabel = (type) => {
  const labelMap = {
    think: '🧠 思考',
    act: '⚡ 行动',
    observe: '👁️ 观察',
    info: '📋 信息',
    error: '❌ 错误'
  };
  return labelMap[type] || type;
};

const addRealtimeStep = (type, title, content) => {
  realtimeSteps.value.push({
    type,
    title,
    content,
    completed: false,
    timestamp: new Date().toLocaleTimeString('zh-CN')
  });
};

const markLastStepCompleted = () => {
  if (realtimeSteps.value.length > 0) {
    realtimeSteps.value[realtimeSteps.value.length - 1].completed = true;
  }
};

const getEdgePath = (edge) => {
  const sourceNode = getNodeById(edge.source);
  const targetNode = getNodeById(edge.target);
  
  if (!sourceNode || !targetNode) return '';
  
  const sourceX = sourceNode.position.x + 180;
  const sourceY = sourceNode.position.y + 30;
  const targetX = targetNode.position.x;
  const targetY = targetNode.position.y + 30;
  
  const sourceEdges = edges.value.filter(e => e.source === edge.source);
  const targetEdges = edges.value.filter(e => e.target === edge.target);
  const edgeIndex = sourceEdges.findIndex(e => e.id === edge.id);
  const targetEdgeIndex = targetEdges.findIndex(e => e.id === edge.id);
  const totalEdgesFromSource = sourceEdges.length;
  const totalEdgesToTarget = targetEdges.length;
  
  let totalOffset = 0;
  if (totalEdgesFromSource > 1 || totalEdgesToTarget > 1) {
    const spacing = 30;
    
    const avgIndex = (edgeIndex + targetEdgeIndex) / 2;
    const maxCount = Math.max(totalEdgesFromSource, totalEdgesToTarget);
    const totalHeight = (maxCount - 1) * spacing;
    const startOffset = -totalHeight / 2;
    totalOffset = startOffset + avgIndex * spacing;
  }
  
  return getEdgePathByType(edgeType, sourceX, sourceY, targetX, targetY, totalOffset);
};

const zoomIn = () => {
  zoom.value = Math.min(MAX_ZOOM, zoom.value + ZOOM_STEP);
};

const zoomOut = () => {
  zoom.value = Math.max(MIN_ZOOM, zoom.value - ZOOM_STEP);
};

const resetZoom = () => {
  zoom.value = 1;
};

const onWheel = (event) => {
  event.preventDefault();
  const delta = event.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
  const newZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom.value + delta));
  
  if (newZoom !== zoom.value) {
    zoom.value = newZoom;
  }
};

const onDragStart = (event, nodeType) => {
  event.dataTransfer.setData('nodeType', nodeType);
  event.dataTransfer.effectAllowed = 'move';
};

const onDragOver = (event) => {
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
};

const onDrop = (event) => {
  const type = event.dataTransfer.getData('nodeType');
  if (!type) return;
  
  const canvasEl = event.currentTarget;
  const rect = canvasEl.getBoundingClientRect();
  const position = {
    x: (event.clientX - rect.left + canvasEl.scrollLeft) / zoom.value - 75,
    y: (event.clientY - rect.top + canvasEl.scrollTop) / zoom.value - 25
  };
  
  const nodeData = {
    label: nodeTypes.find(n => n.type === type)?.label || type,
    description: ''
  };
  
  if (type === 'loop') {
    nodeData.loopCondition = 'i < 5';
    nodeData.loopMax = 10;
    nodeData.loopVariable = 'i';
  } else if (type === 'iteration') {
    nodeData.iterationList = '';
    nodeData.iterationVariable = 'item';
  } else if (type === 'llm') {
    nodeData.temperature = 0.7;
    nodeData.maxTokens = 1024;
    nodeData.stream = false;
    nodeData.skillIds = [];
    nodeData.enableReact = true;
    nodeData.maxIterations = 5;
  }
  
  const newNode = {
    id: `${type}-${Date.now()}`,
    type,
    position,
    data: nodeData
  };
  nodes.value.push(newNode);
};

const onNodeClick = (node) => {
  selectedEdge.value = null;
  selectedNode.value = node;
};

const onNodeMouseDown = (event, node) => {
  if (event.target.classList.contains('connection-point')) return;
  
  draggingNode.value = node;
  const canvasEl = canvas.value;
  const rect = canvasEl.getBoundingClientRect();
  dragOffset.value = {
    x: (event.clientX - rect.left) / zoom.value - node.position.x,
    y: (event.clientY - rect.top) / zoom.value - node.position.y
  };
  event.preventDefault();
};

const onEdgeClick = (edge) => {
  selectedNode.value = null;
  selectedEdge.value = edge;
};

const onOutputPointMouseDown = (event, node) => {
  drawingEdge.value = true;
  edgeStartNode.value = node;
  edgeStartPoint.value = {
    x: node.position.x + 180,
    y: node.position.y + 30
  };
  currentMousePos.value = { ...edgeStartPoint.value };
};

const onInputPointMouseDown = (event, node) => {
  event.stopPropagation();
};

const onInputPointMouseUp = (event, node) => {
  if (drawingEdge.value && edgeStartNode.value && edgeStartNode.value.id !== node.id) {
    const exists = edges.value.find(e => 
      e.source === edgeStartNode.value.id && e.target === node.id
    );
    
    if (!exists) {
      const newEdge = {
        id: `edge-${Date.now()}`,
        source: edgeStartNode.value.id,
        target: node.id
      };
      edges.value.push(newEdge);
      ElMessage.success('连线创建成功');
    } else {
      ElMessage.warning('连线已存在');
    }
  }
  
  drawingEdge.value = false;
  edgeStartNode.value = null;
};

const onMouseMove = (event) => {
  if (drawingEdge.value) {
    const canvasEl = canvas.value;
    const rect = canvasEl.getBoundingClientRect();
    currentMousePos.value = {
      x: (event.clientX - rect.left + canvasEl.scrollLeft) / zoom.value,
      y: (event.clientY - rect.top + canvasEl.scrollTop) / zoom.value
    };
  }
  
  if (draggingNode.value) {
    const canvasEl = canvas.value;
    const rect = canvasEl.getBoundingClientRect();
    draggingNode.value.position = {
      x: (event.clientX - rect.left + canvasEl.scrollLeft) / zoom.value - dragOffset.value.x,
      y: (event.clientY - rect.top + canvasEl.scrollTop) / zoom.value - dragOffset.value.y
    };
  }
};

const onMouseUp = () => {
  drawingEdge.value = false;
  edgeStartNode.value = null;
  draggingNode.value = null;
};

const deleteSelectedNode = () => {
  if (selectedNode.value) {
    edges.value = edges.value.filter(e => 
      e.source !== selectedNode.value.id && e.target !== selectedNode.value.id
    );
    
    const index = nodes.value.findIndex(n => n.id === selectedNode.value.id);
    if (index > -1) {
      nodes.value.splice(index, 1);
    }
    selectedNode.value = null;
    ElMessage.success('节点已删除');
  }
};

const deleteSelectedEdge = () => {
  if (selectedEdge.value) {
    const index = edges.value.findIndex(e => e.id === selectedEdge.value.id);
    if (index > -1) {
      edges.value.splice(index, 1);
    }
    selectedEdge.value = null;
    ElMessage.success('连线已删除');
  }
};

const saveWorkflow = async () => {
  if (props.workflowId) {
    saving.value = true;
    try {
      const definition = {
        nodes: JSON.parse(JSON.stringify(nodes.value)),
        edges: JSON.parse(JSON.stringify(edges.value))
      };
      
      await updateWorkflow(props.workflowId, {
        definition
      });
      ElMessage.success('保存成功');
    } catch (error) {
      safeConsole.error('保存工程图失败:', error);
      ElMessage.error('保存失败: ' + (error.message || error));
    } finally {
      saving.value = false;
    }
  }
  emit('save', { 
    nodes: JSON.parse(JSON.stringify(nodes.value)), 
    edges: JSON.parse(JSON.stringify(edges.value)) 
  });
};

const executeWorkflowDialog = () => {
  executeDialog.value = true;
  executeInput.value = '{}';
  executeResult.value = null;
};

watch(() => executeDialog.value, (newVal) => {
  if (newVal) {
    realtimeSteps.value = [];
    executeResult.value = null;
    currentInput.value = '';
    latestResponse.value = '';
  }
});

const clearDialogHistory = () => {
  dialogHistory.value = [];
  currentInput.value = '';
  latestResponse.value = '';
  realtimeSteps.value = [];
  executeResult.value = null;
  ElMessage.success('对话历史已清空');
};

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
  };
  return iconMap[type] || 'ℹ️';
};

const startTypingAnimation = () => {
  const dots = ['.', '..', '...', '..', '.'];
  let index = 0;
  typingInterval = setInterval(() => {
    typingDots.value = dots[index];
    index = (index + 1) % dots.length;
  }, 350);
};

const stopTypingAnimation = () => {
  if (typingInterval) {
    clearInterval(typingInterval);
    typingInterval = null;
    typingDots.value = '';
  }
};

const doExecute = async () => {
  if (!props.workflowId && !props.agentId) {
    ElMessage.warning('请先创建工程图或智能体');
    return;
  }
  
  if (!currentInput.value.trim()) {
    ElMessage.warning('请输入内容');
    return;
  }
  
  realtimeSteps.value = [];
  currentProcess.value = [];
  executing.value = true;
  
  startTypingAnimation();
  
  try {
    const userMessage = {
      role: 'user',
      content: currentInput.value,
      time: new Date().toLocaleTimeString('zh-CN')
    };
    dialogHistory.value.push(userMessage);
    
    assistantMessage.value = {
      role: 'assistant',
      content: '',
      time: new Date().toLocaleTimeString('zh-CN'),
      process: []
    };
    dialogHistory.value.push(assistantMessage.value);
    
    addRealtimeStep('info', '开始执行', `输入文本: ${currentInput.value.trim().substring(0, 100)}...`);
    markLastStepCompleted();
    
    const input = {
      text: currentInput.value.trim(),
      history: [...dialogHistory.value.slice(0, -1)]
    };
    
    currentInput.value = '';
    
    if (props.agentId) {
      const controller = executeAgentGraphAuto(props.agentId, input, {
        onStart: () => {
          addRealtimeStep('info', '准备执行', '正在建立SSE连接...');
          markLastStepCompleted();
        },
        onData: (data) => {
          handleSSEData(data);
        },
        onComplete: (result) => {
          addRealtimeStep('info', '执行完成', '智能体执行完成');
          markLastStepCompleted();
          ElMessage.success('执行完成');
          
          if (result) {
            handleNonSSEData(result);
          }
          
          stopTypingAnimation();
          executing.value = false;
          currentAbortController.value = null;
        },
        onError: (error) => {
          addRealtimeStep('error', '执行失败', error.message || '未知错误');
          markLastStepCompleted();
          ElMessage.error('执行失败: ' + (error.message || '未知错误'));
          stopTypingAnimation();
          executing.value = false;
          currentAbortController.value = null;
        }
      });
      currentAbortController.value = controller;
    } else {
      const result = await apiExecuteWorkflow(props.workflowId, input);
      
      handleNonSSEData(result);
      stopTypingAnimation();
      executing.value = false;
      currentAbortController.value = null;
    }
    
    emit('execute', executeResult.value);
  } catch (error) {
    safeConsole.error('执行失败:', error);
    
    if (assistantMessage.value) {
      assistantMessage.value.content = '执行失败: ' + (error.message || '未知错误');
    } else {
      const errorMessage = {
        role: 'assistant',
        content: '执行失败: ' + (error.message || '未知错误'),
        time: new Date().toLocaleTimeString('zh-CN')
      };
      dialogHistory.value.push(errorMessage);
    }
    latestResponse.value = '执行失败: ' + (error.message || '未知错误');
    
    addRealtimeStep('error', '执行失败', error.message || '未知错误');
    markLastStepCompleted();
    
    ElMessage.error('执行失败: ' + (error.message || '未知错误'));
    
    stopTypingAnimation();
    executing.value = false;
    currentAbortController.value = null;
  }
};

const abortExecution = () => {
  if (currentAbortController.value) {
    currentAbortController.value.abort();
    currentAbortController.value = null;
    executing.value = false;
    stopTypingAnimation();
    
    addRealtimeStep('warning', '执行中断', '用户手动中断执行');
    markLastStepCompleted();
    
    if (assistantMessage.value) {
      assistantMessage.value.content = (assistantMessage.value.content || '') + '\n\n[执行被用户中断]';
    }
    
    ElMessage.info('执行已中断');
  }
};

const handleSSEData = (data) => {
  switch (data.type) {
    case 'start':
      addRealtimeStep('info', data.label || '开始', data.message || '执行开始');
      markLastStepCompleted();
      break;
    
    case 'info':
      addRealtimeStep('info', data.label || '信息', data.message || '');
      markLastStepCompleted();
      break;
    
    case 'thinking':
      addRealtimeStep('think', data.label || '思考', data.message || data.content || '');
      markLastStepCompleted();
      break;
    
    case 'thinkingStream':
      const rawContent = data.fullContent || data.content || '';
      if (assistantMessage.value) {
        assistantMessage.value.content = rawContent;
      }
      addRealtimeStep('think', data.label || '思考中', rawContent);
      break;
    
    case 'thinkingResult':
      const finalRawContent = data.fullContent || data.content || '';
      addRealtimeStep('think', '思考完成', finalRawContent);
      markLastStepCompleted();
      break;
    
    case 'action':
      addRealtimeStep('act', data.label || '行动', data.message || data.content || '');
      markLastStepCompleted();
      break;
    
    case 'observation':
      addRealtimeStep('observe', data.label || '观察', data.content || '');
      markLastStepCompleted();
      break;
    
    case 'nodeStart':
      addRealtimeStep('info', `执行节点: ${data.nodeLabel || data.nodeType}`, `步骤 ${data.step}`);
      break;
    
    case 'nodeComplete':
      addRealtimeStep('success', `节点完成: ${data.nodeLabel || data.nodeType}`, '');
      markLastStepCompleted();
      break;
    
    case 'cancelled':
      addRealtimeStep('warning', '执行中断', data.message || '执行被用户中断');
      markLastStepCompleted();
      
      if (assistantMessage.value) {
        assistantMessage.value.content = (assistantMessage.value.content || '') + '\n\n[执行被用户中断]';
      }
      
      stopTypingAnimation();
      executing.value = false;
      currentAbortController.value = null;
      break;
    
    case 'complete':
      executeResult.value = {
        result: data.result,
        variables: data.variables
      };
      
      let finalContent = '';
      if (data.variables) {
        finalContent = data.variables.finalReport || 
                      data.variables.response || 
                      data.variables.text || 
                      data.variables.output || 
                      '';
        if (!finalContent && data.variables.llmOutput) {
          finalContent = data.variables.llmOutput.response || data.variables.llmOutput.text || '';
        }
      } else if (data.result) {
        finalContent = data.result.output || data.result.text || '';
      }
      
      if (!finalContent) {
        finalContent = '执行完成';
      }
      
      if (assistantMessage.value) {
        assistantMessage.value.content = finalContent;
      }
      
      latestResponse.value = finalContent;
      
      stopTypingAnimation();
      executing.value = false;
      currentAbortController.value = null;
      break;
    
    case 'error':
      addRealtimeStep('error', data.label || '错误', data.message || '');
      markLastStepCompleted();
      
      if (assistantMessage.value) {
        assistantMessage.value.content = '执行错误: ' + (data.message || '');
      }
      latestResponse.value = '执行错误: ' + (data.message || '');
      
      stopTypingAnimation();
      executing.value = false;
      currentAbortController.value = null;
      break;
  }
};

const formatJsonToDisplay = (content, label) => {
  if (!content) return content;
  
  let jsonData = null;
  let textToParse = content;
  
  try {
    jsonData = JSON.parse(textToParse);
  } catch {
    try {
      const jsonMatch = textToParse.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        jsonData = JSON.parse(jsonMatch[0]);
      }
    } catch {
      return content;
    }
  }
  
  if (!jsonData) return content;
  
  let result = '';
  
  if (label?.includes('需求')) {
    result = '📊 需求分析结果\n';
    if (jsonData.projectType) result += `• 项目类型: ${jsonData.projectType}\n`;
    if (jsonData.targetUsers) result += `• 目标用户: ${jsonData.targetUsers}\n`;
    if (jsonData.businessGoals) result += `• 业务目标: ${jsonData.businessGoals}\n`;
    if (Array.isArray(jsonData.coreFeatures) && jsonData.coreFeatures.length > 0) {
      result += '• 核心功能:\n';
      jsonData.coreFeatures.forEach((f, i) => {
        result += `  ${i+1}. ${f}\n`;
      });
    }
  } else if (label?.includes('任务') || jsonData.totalTask || jsonData.subtasks) {
    result = '📋 任务分解结果\n';
    if (jsonData.originalTask || jsonData.totalTask) {
      result += `• 总任务: ${jsonData.originalTask || jsonData.totalTask}\n`;
    }
    if (jsonData.totalHours) {
      result += `• 总工时: ${jsonData.totalHours} 小时\n`;
    }
    if (Array.isArray(jsonData.subtasks) && jsonData.subtasks.length > 0) {
      result += '• 子任务清单:\n';
      jsonData.subtasks.forEach((task, i) => {
        const priorityIcon = task.priority === 'high' ? '🔴' : task.priority === 'medium' ? '🟡' : '🟢';
        const name = task.name || task.taskName || '';
        const estimate = task.estimatedHours ? ` (${task.estimatedHours}小时)` : '';
        result += `  ${i+1}. ${priorityIcon} ${name}${estimate}\n`;
        if (task.description || task.taskDescription) {
          result += `    ${task.description || task.taskDescription}\n`;
        }
      });
    }
    if (Array.isArray(jsonData.milestones) && jsonData.milestones.length > 0) {
      result += '• 里程碑:\n';
      jsonData.milestones.forEach((m, i) => {
        const milestoneEstimate = m.estimatedHours ? ` (${m.estimatedHours}小时)` : '';
        result += `  ${i+1}. ${m.name}${milestoneEstimate}\n`;
      });
    }
  } else if (label?.includes('评估')) {
    result = '✅ 质量评估结果\n';
    const score = jsonData.qualityScore != null ? jsonData.qualityScore : 'N/A';
    if (score !== 'N/A') result += `• 质量评分: ${score}/100\n`;
    if (jsonData.feedback) result += `• 评估反馈: ${jsonData.feedback}\n`;
    if (Array.isArray(jsonData.strengths) && jsonData.strengths.length > 0) {
      result += '• 优点:\n';
      jsonData.strengths.forEach((s, i) => {
        result += `  ${i+1}. ${s}\n`;
      });
    }
    if (Array.isArray(jsonData.weaknesses) && jsonData.weaknesses.length > 0) {
      result += '• 可改进:\n';
      jsonData.weaknesses.forEach((w, i) => {
        result += `  ${i+1}. ${w}\n`;
      });
    }
  } else {
    result = '📄 内容:\n' + content;
  }
  
  return result || content;
};

const updateAssistantMessage = () => {
  if (assistantMessage.value) {
    assistantMessage.value.process = [...currentProcess.value];
    if (!assistantMessage.value.content) {
      assistantMessage.value.content = '思考中...';
    }
    const lastIndex = dialogHistory.value.length - 1;
    if (lastIndex >= 0 && dialogHistory.value[lastIndex] === assistantMessage.value) {
      dialogHistory.value = [...dialogHistory.value];
    }
  }
};

const handleNonSSEData = (result) => {
  if (!result) return;
  
  executeResult.value = result;
  
  let assistantResponse = '';
  if (typeof result === 'string') {
    assistantResponse = result;
  } else if (result.output || result.result || result.text || result.response) {
    assistantResponse = result.output || result.result || result.text || result.response;
  } else if (result.variables) {
    const vars = result.variables;
    assistantResponse = vars.finalReport || vars.response || vars.text || vars.output || '';
    if (!assistantResponse && vars.llmOutput) {
      assistantResponse = vars.llmOutput.response || vars.llmOutput.text || '';
    }
  }
  
  if (!assistantResponse) {
    assistantResponse = '执行完成';
  }
  
  if (assistantMessage.value) {
    assistantMessage.value.content = assistantResponse;
  }
  
  latestResponse.value = assistantResponse;
};

const exportWorkflow = () => {
  const data = {
    nodes: nodes.value,
    edges: edges.value
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'workflow.json';
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success('导出成功');
};

const importWorkflow = () => {
  fileInput.value.click();
};

const transformNode = (node) => {
  if (!node) return null;
  
  const nodeType = node.type || 'default';
  const position = node.position || node.data?.position || { x: Math.random() * 500, y: Math.random() * 300 };
  
  const transformed = {
    id: node.id || `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    type: nodeType,
    position: position,
    data: {
      label: node.name || node.data?.label || '节点',
      description: node.data?.description || ''
    }
  };

  if (nodeType === 'llm') {
    transformed.data.prompt = node.config?.prompt || node.data?.prompt || '';
    transformed.data.modelId = node.config?.model_id || node.data?.modelId || null;
    transformed.data.temperature = node.data?.temperature ?? 0.7;
    transformed.data.maxTokens = node.data?.maxTokens ?? 1024;
    transformed.data.stream = node.data?.stream ?? false;
    transformed.data.skillIds = node.data?.skillIds || node.data?.skill_ids || [];
    transformed.data.outputVar = node.data?.outputVar || '';
  } else if (nodeType === 'tool') {
    transformed.data.toolName = node.config?.tool_name || node.data?.toolName || '';
    transformed.data.description = node.config?.description || node.data?.description || '';
  } else if (nodeType === 'decision' || nodeType === 'condition') {
    transformed.type = 'condition';
    transformed.data.condition = node.config?.condition || node.data?.condition || '';
  }

  return transformed;
};

const transformEdge = (edge, index) => {
  if (!edge || !edge.source || !edge.target) return null;
  
  return {
    id: edge.id || `${edge.source}-${edge.target}-${index}`,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle || null,
    targetHandle: edge.targetHandle || null,
    condition: edge.condition || null,
    type: edge.type || 'default'
  };
};

const handleFileImport = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);
      
      let importData = data;
      if (data.agent?.graph_definition) {
        importData = data.agent.graph_definition;
      } else if (data.graph_definition) {
        importData = data.graph_definition;
      }
      
      selectedNode.value = null;
      selectedEdge.value = null;
      
      if (importData.nodes) {
        const transformedNodes = importData.nodes.map(transformNode).filter(
          node => node && node.id && node.type
        );
        
        nodes.value.splice(0, nodes.value.length, ...transformedNodes);
      }
      
      if (importData.edges) {
        const transformedEdges = importData.edges.map((edge, index) => transformEdge(edge, index)).filter(
          edge => edge && edge.source && edge.target
        );
        
        edges.value.splice(0, edges.value.length, ...transformedEdges);
      }
      
      ElMessage.success('导入成功');
    } catch (err) {
      ElMessage.error('文件格式错误');
      console.error(err);
    }
  };
  reader.readAsText(file);
  event.target.value = '';
};

const fetchAgents = async () => {
  try {
    const result = await getAgents({ limit: 1000 });
    agents.value = result.data?.items || result.data || [];
  } catch (error) {
    safeConsole.error(error);
  }
};

const fetchSkills = async () => {
  try {
    const result = await getSkills({ limit: 1000 });
    skills.value = result.data?.items || result.data || [];
  } catch (error) {
    safeConsole.error(error);
  }
};

const fetchModels = async () => {
  try {
    const result = await getModelList({ limit: 1000 });
    models.value = result.data?.items || result.data || [];
  } catch (error) {
    safeConsole.error(error);
  }
};

onMounted(() => {
  fetchAgents();
  fetchSkills();
  fetchModels();
  
  if (props.initialNodes.length > 0) {
    nodes.value = props.initialNodes;
  }
  if (props.initialEdges.length > 0) {
    edges.value = props.initialEdges;
  }
});

watch(() => props.initialNodes, (newNodes) => {
  if (newNodes && newNodes.length > 0) {
    const clonedNodes = JSON.parse(JSON.stringify(newNodes)).filter(
      node => node && node.id && node.type
    );
    if (clonedNodes.length > 0) {
      selectedNode.value = null;
      nodes.value.splice(0, nodes.value.length, ...clonedNodes);
    }
  }
}, { immediate: true, deep: true });

watch(() => props.initialEdges, (newEdges) => {
  if (newEdges && newEdges.length > 0) {
    const clonedEdges = JSON.parse(JSON.stringify(newEdges)).filter(
      edge => edge && edge.source && edge.target
    );
    if (clonedEdges.length > 0) {
      selectedEdge.value = null;
      edges.value.splice(0, edges.value.length, ...clonedEdges);
    }
  }
}, { immediate: true, deep: true });
</script>

<style scoped>
.langgraph-editor {
  height: calc(100vh - 100px);
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
  align-items: center;
  gap: 8px;
}

.canvas-zoom-controls {
  position: fixed;
  bottom: 30px;
  right: 50px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.95);
  padding: 12px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  z-index: 100;
  .el-button {
    margin-left: 3px !important;
  }
}

.canvas-zoom-value {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
  min-width: 40px;
  text-align: center;
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
  width: 5000px;
  height: 5000px;
  min-width: 100%;
  min-height: 100%;
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

.wechat-style-dialog .el-dialog__body {
  padding: 0;
  height: 600px;
  overflow: hidden;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
  min-height: 300px;
  max-height: 400px;
  background: #f5f7fa;
  scrollbar-width: thin;
  scrollbar-color: #c0c4cc #f5f7fa;
}

.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f5f7fa;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #909399;
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
  background: white;
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

.message-streaming {
  background: linear-gradient(135deg, #fdf6ec 0%, white 100%);
  border-left: 3px solid #e6a23c;
}

.typing-dots {
  display: inline-block;
  margin-left: 4px;
  vertical-align: text-bottom;
  font-weight: bold;
  color: #606266;
  min-width: 20px;
}

.message.assistant .message-content {
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  line-height: 1.7;
  color: #303133;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.message.assistant .message-content::first-letter {
  font-weight: 600;
}

.message-streaming .message-content {
  animation: contentFadeIn 0.3s ease;
}

@keyframes contentFadeIn {
  from {
    opacity: 0.7;
  }
  to {
    opacity: 1;
  }
}

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
  background: white;
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
  background: white;
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

.chat-input-area {
  padding-top: 20px;
  background: white;
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