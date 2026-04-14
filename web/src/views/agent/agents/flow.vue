<template>
  <div class="agent-flow">
    <div class="toolbar">
      <span class="flow-name">智能体流程图</span>
      <div class="toolbar-right">
        <el-button type="success" @click="executeFlow" :loading="executing">
          <el-icon><VideoPlay /></el-icon>
          执行
        </el-button>
        <el-button type="primary" @click="saveFlow" :loading="saving">
          <el-icon><Check /></el-icon>
          保存
        </el-button>
      </div>
    </div>
    
    <div class="editor-container">
      <div class="node-panel">
        <div class="panel-title">基础节点</div>
        <div 
          v-for="nodeType in nodeTypes.filter(n => n.category === 'basic')" 
          :key="nodeType.type"
          class="node-item"
          draggable="true"
          @dragstart="onDragStart($event, nodeType.type)"
        >
          <el-icon :size="20"><component :is="nodeType.icon" /></el-icon>
          <span>{{ nodeType.label }}</span>
        </div>
        
        <div class="panel-title" style="margin-top: 15px">智能体节点</div>
        <div 
          v-for="nodeType in nodeTypes.filter(n => n.category === 'agent')" 
          :key="nodeType.type"
          class="node-item"
          draggable="true"
          @dragstart="onDragStart($event, nodeType.type)"
        >
          <el-icon :size="20"><component :is="nodeType.icon" /></el-icon>
          <span>{{ nodeType.label }}</span>
        </div>
        
        <div class="panel-title" style="margin-top: 15px">转换节点</div>
        <div 
          v-for="nodeType in nodeTypes.filter(n => n.category === 'transform')" 
          :key="nodeType.type"
          class="node-item"
          draggable="true"
          @dragstart="onDragStart($event, nodeType.type)"
        >
          <el-icon :size="20"><component :is="nodeType.icon" /></el-icon>
          <span>{{ nodeType.label }}</span>
        </div>
        
        <div class="panel-title" style="margin-top: 15px">工具节点</div>
        <div 
          v-for="nodeType in nodeTypes.filter(n => n.category === 'tool')" 
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
          <p>• 点击节点选中并查看详情</p>
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
                class="agent-edge"
                :class="{ 'selected': selectedEdge?.id === edge.id }"
                marker-end="url(#arrowhead)"
              />
            </g>
            <path v-if="drawingEdge" :d="tempEdgePath" class="temp-edge" />
          </svg>
          
          <div 
            v-for="node in nodes" 
            :key="node.id"
            class="agent-node"
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
                <span v-if="node.type === 'llm' && getNodeLLMName(node)" class="node-subtitle">{{ getNodeLLMName(node) }}</span>
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
          <div class="panel-title">节点信息</div>
          
          <!-- 下一步节点配置 -->
          <div class="panel-title">下一步节点配置</div>
          <el-form label-width="80px" size="small">
            <el-form-item label="目标节点">
              <div class="target-nodes-container" style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; border: 1px solid #e0e0e0;">
                <div v-if="targetNodes.length === 0" style="text-align: center; color: #909399; padding: 20px;">
                  无目标节点
                </div>
                <div v-else class="target-nodes-list">
                  <div v-for="(node, index) in targetNodes" :key="node.id" class="target-node-item" style="display: flex; align-items: center; margin-bottom: 10px; padding: 8px 12px; background-color: #fff; border-radius: 4px; border: 1px solid #e0e0e0;">
                    <el-icon :size="16" style="color: #409eff; margin-right: 8px;">
                      <component :is="nodeTypes.find(n => n.type === node.type)?.icon || Document" />
                    </el-icon>
                    <span style="flex: 1; color: #303133;">{{ node.data.label }}</span>
                    <el-tag size="small" type="info" style="margin-left: 10px;">
                      {{ node.type }}
                    </el-tag>
                  </div>
                </div>
              </div>
            </el-form-item>
          </el-form>
          
          <template v-if="selectedNode.type === 'agent'">
            <el-card v-if="selectedAgent" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>智能体详情</span>
                </div>
              </template>
              <div class="agent-info">
                <p><strong>名称：</strong>{{ selectedAgent.name }}</p>
                <p><strong>描述：</strong>{{ selectedAgent.description }}</p>
                <p><strong>状态：</strong>
                  <el-tag :type="getStatusType(selectedAgent.status)">
                    {{ getStatusName(selectedAgent.status) }}
                  </el-tag>
                </p>
                <p><strong>记忆容量：</strong>{{ selectedAgent.memory_capacity }} 条</p>
                <p><strong>关联大模型：</strong>{{ selectedAgent.llm_model_name || '未设置' }}</p>
                <p><strong>关联技能：</strong>{{ selectedAgent.skill_count }} 个</p>
                <p><strong>关联工作流：</strong>{{ selectedAgent.workflow_count }} 个</p>
                <p><strong>关联对话流：</strong>{{ selectedAgent.dialog_flow_count }} 个</p>
                <p><strong>创建时间：</strong>{{ formatDate(selectedAgent.created_at) }}</p>
                <p><strong>更新时间：</strong>{{ formatDate(selectedAgent.updated_at) }}</p>
              </div>
              <el-button type="primary" size="small" @click="editAgent(selectedAgent.id)" style="width: 100%; margin-top: 10px">
                编辑智能体
              </el-button>
            </el-card>
            <el-empty v-else description="未选择智能体" />
          </template>
          <template v-if="selectedNode.type === 'workflow'">
            <div class="panel-title">工作流配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="选择工作流">
                <el-select v-model="selectedNode.data.workflowId" @change="updateWorkflowSelection" style="width: 100%">
                  <el-option
                    v-for="workflow in workflows"
                    :key="workflow.id"
                    :label="workflow.name"
                    :value="workflow.id"
                  />
                </el-select>
              </el-form-item>
            </el-form>
            <el-card v-if="selectedWorkflow" shadow="hover" style="margin-top: 10px">
              <template #header>
                <div class="card-header">
                  <span>工作流详情</span>
                </div>
              </template>
              <div class="workflow-info">
                <p><strong>名称：</strong>{{ selectedWorkflow.name }}</p>
                <p><strong>描述：</strong>{{ selectedWorkflow.description }}</p>
                <p><strong>状态：</strong>
                  <el-tag :type="getStatusType(selectedWorkflow.status)">
                    {{ getStatusName(selectedWorkflow.status) }}
                  </el-tag>
                </p>
                <p><strong>创建时间：</strong>{{ formatDate(selectedWorkflow.created_at) }}</p>
                <p><strong>更新时间：</strong>{{ formatDate(selectedWorkflow.updated_at) }}</p>
              </div>
              <el-button type="primary" size="small" @click="editWorkflow(selectedWorkflow.id)" style="width: 100%; margin-top: 10px">
                编辑工作流
              </el-button>
            </el-card>
          </template>
          <template v-if="selectedNode.type === 'dialog_flow'">
            <div class="panel-title">对话流配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="选择对话流">
                <el-select v-model="selectedNode.data.dialogFlowId" @change="updateDialogFlowSelection" style="width: 100%">
                  <el-option
                    v-for="dialogFlow in dialogFlows"
                    :key="dialogFlow.id"
                    :label="dialogFlow.name"
                    :value="dialogFlow.id"
                  />
                </el-select>
              </el-form-item>
            </el-form>
            <el-card v-if="selectedDialogFlow" shadow="hover" style="margin-top: 10px">
              <template #header>
                <div class="card-header">
                  <span>对话流详情</span>
                </div>
              </template>
              <div class="dialog-flow-info">
                <p><strong>名称：</strong>{{ selectedDialogFlow.name }}</p>
                <p><strong>描述：</strong>{{ selectedDialogFlow.description }}</p>
                <p><strong>状态：</strong>
                  <el-tag :type="getStatusType(selectedDialogFlow.status)">
                    {{ getStatusName(selectedDialogFlow.status) }}
                  </el-tag>
                </p>
                <p><strong>创建时间：</strong>{{ formatDate(selectedDialogFlow.created_at) }}</p>
                <p><strong>更新时间：</strong>{{ formatDate(selectedDialogFlow.updated_at) }}</p>
              </div>
              <el-button type="primary" size="small" @click="editDialogFlow(selectedDialogFlow.id)" style="width: 100%; margin-top: 10px">
                编辑对话流
              </el-button>
            </el-card>
          </template>
          <template v-if="selectedNode.type === 'llm'">
            <div class="panel-title">大模型配置</div>
            <div style="margin-bottom: 10px; font-size: 12px; color: #999;">
              大模型数量: {{ llms.length }}
            </div>
            <el-form label-width="80px" size="small">
              <el-form-item label="选择模型">
                <el-select v-model="selectedNode.data.llm_id" placeholder="请选择大模型" @change="onLLMChange" style="width: 100%">
                  <el-option v-for="llm in llms" :key="llm.id" :value="llm.id">
                    <span>{{ llm.provider_name }} - {{ llm.model_name }}</span>
                  </el-option>
                </el-select>
              </el-form-item>
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
            </el-form>
            <el-card v-if="selectedLLM" shadow="hover" style="margin-top: 10px">
              <template #header>
                <div class="card-header">
                  <span>大模型详情</span>
                </div>
              </template>
              <div class="llm-info">
                <p><strong>名称：</strong>{{ selectedLLM.model_name }}</p>
                <p><strong>提供者：</strong>{{ selectedLLM.provider_name }}</p>
                <p><strong>描述：</strong>{{ selectedLLM.description }}</p>
                <p><strong>状态：</strong>
                  <el-tag :type="getStatusType(selectedLLM.status)">
                    {{ getStatusName(selectedLLM.status) }}
                  </el-tag>
                </p>
              </div>
            </el-card>
          </template>
          
          <!-- Dify 风格节点 - 代码执行 -->
          <template v-if="selectedNode.type === 'code'">
            <div class="panel-title">代码执行配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="代码语言">
                <el-select v-model="selectedNode.data.language" style="width: 100%">
                  <el-option label="Python" value="python" />
                  <el-option label="JavaScript" value="javascript" />
                </el-select>
              </el-form-item>
              <el-form-item label="代码内容">
                <el-input v-model="selectedNode.data.code" type="textarea" :rows="6" placeholder="# 输入代码" />
              </el-form-item>
            </el-form>
          </template>
          
          <!-- Dify 风格节点 - 模板转换 -->
          <template v-if="selectedNode.type === 'template'">
            <div class="panel-title">模板转换配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="模板内容">
                <el-input v-model="selectedNode.data.template" type="textarea" :rows="4" placeholder="使用 {{variable}} 引用变量" />
              </el-form-item>
            </el-form>
          </template>
          
          <!-- Dify 风格节点 - 变量聚合器 -->
          <template v-if="selectedNode.type === 'variable_aggregator'">
            <div class="panel-title">变量聚合器配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="输入变量">
                <el-input v-model="selectedNode.data.input_vars" type="textarea" :rows="3" placeholder="每行一个变量名" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_var" placeholder="聚合后的变量名" />
              </el-form-item>
            </el-form>
          </template>
          
          <!-- Dify 风格节点 - HTTP 请求 -->
          <template v-if="selectedNode.type === 'http'">
            <div class="panel-title">HTTP 请求配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="请求方法">
                <el-select v-model="selectedNode.data.method" style="width: 100%">
                  <el-option label="GET" value="GET" />
                  <el-option label="POST" value="POST" />
                  <el-option label="PUT" value="PUT" />
                  <el-option label="DELETE" value="DELETE" />
                </el-select>
              </el-form-item>
              <el-form-item label="请求URL">
                <el-input v-model="selectedNode.data.url" placeholder="https://api.example.com" />
              </el-form-item>
              <el-form-item label="请求头">
                <el-input v-model="selectedNode.data.headers" type="textarea" :rows="2" placeholder="JSON格式" />
              </el-form-item>
              <el-form-item label="请求体">
                <el-input v-model="selectedNode.data.body" type="textarea" :rows="3" placeholder="JSON格式" />
              </el-form-item>
            </el-form>
          </template>
          
          <!-- Dify 风格节点 - 列表操作 -->
          <template v-if="selectedNode.type === 'list_operation'">
            <div class="panel-title">列表操作配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="操作类型">
                <el-select v-model="selectedNode.data.operation" style="width: 100%">
                  <el-option label="过滤" value="filter" />
                  <el-option label="映射" value="map" />
                  <el-option label="排序" value="sort" />
                  <el-option label="去重" value="unique" />
                </el-select>
              </el-form-item>
              <el-form-item label="输入列表">
                <el-input v-model="selectedNode.data.input_list" placeholder="变量名" />
              </el-form-item>
            </el-form>
          </template>
          
          <!-- Dify 风格节点 - 文档提取器 -->
          <template v-if="selectedNode.type === 'document_extractor'">
            <div class="panel-title">文档提取器配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="文档变量">
                <el-input v-model="selectedNode.data.document_var" placeholder="文档内容变量名" />
              </el-form-item>
              <el-form-item label="提取规则">
                <el-input v-model="selectedNode.data.extract_rules" type="textarea" :rows="3" placeholder="提取规则配置" />
              </el-form-item>
            </el-form>
          </template>
          
          <!-- Dify 风格节点 - 变量赋值 -->
          <template v-if="selectedNode.type === 'variable_assigner'">
            <div class="panel-title">变量赋值配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="变量名">
                <el-input v-model="selectedNode.data.var_name" placeholder="变量名称" />
              </el-form-item>
              <el-form-item label="变量值">
                <el-input v-model="selectedNode.data.var_value" type="textarea" :rows="2" placeholder="变量值或表达式" />
              </el-form-item>
            </el-form>
          </template>
          
          <!-- Dify 风格节点 - 参数提取器 -->
          <template v-if="selectedNode.type === 'parameter_extractor'">
            <div class="panel-title">参数提取器配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="输入文本">
                <el-input v-model="selectedNode.data.input_text" placeholder="输入文本变量名" />
              </el-form-item>
              <el-form-item label="提取参数">
                <el-input v-model="selectedNode.data.parameters" type="textarea" :rows="3" placeholder="每行一个参数名" />
              </el-form-item>
            </el-form>
          </template>
          
          <!-- 输入节点配置 -->
          <template v-if="selectedNode.type === 'input'">
            <div class="panel-title">输入配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="输入类型">
                <el-select v-model="selectedNode.data.input_type" style="width: 100%">
                  <el-option label="文本" value="text" />
                  <el-option label="文件" value="file" />
                  <el-option label="表单" value="form" />
                  <el-option label="JSON" value="json" />
                </el-select>
              </el-form-item>
              <el-form-item label="输入提示">
                <el-input v-model="selectedNode.data.input_placeholder" placeholder="用户输入提示" />
              </el-form-item>
            </el-form>
          </template>
          
          <!-- 输出节点配置 -->
          <template v-if="selectedNode.type === 'output'">
            <div class="panel-title">输出配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="输出类型">
                <el-select v-model="selectedNode.data.output_type" style="width: 100%">
                  <el-option label="文本" value="text" />
                  <el-option label="JSON" value="json" />
                  <el-option label="文件" value="file" />
                </el-select>
              </el-form-item>
              <el-form-item label="输出内容">
                <el-input v-model="selectedNode.data.output_content" type="textarea" :rows="4" placeholder="输出内容或变量表达式" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_var" placeholder="存储输出结果的变量名" />
              </el-form-item>
            </el-form>
          </template>
          
          <!-- 知识检索节点配置 -->
          <template v-if="selectedNode.type === 'knowledge_retrieval'">
            <div class="panel-title">知识检索配置</div>
            <el-form label-width="80px" size="small">
              <el-form-item label="节点名称">
                <el-input v-model="selectedNode.data.label" @change="updateNodeLabel" />
              </el-form-item>
              <el-form-item label="知识库">
                <el-select v-model="selectedNode.data.knowledge_base" style="width: 100%">
                  <el-option label="默认知识库" value="default" />
                  <el-option label="用户知识库" value="user" />
                </el-select>
              </el-form-item>
              <el-form-item label="检索查询">
                <el-input v-model="selectedNode.data.query" type="textarea" :rows="2" placeholder="检索关键词或语句" />
              </el-form-item>
              <el-form-item label="检索数量">
                <el-input-number v-model="selectedNode.data.top_k" :min="1" :max="100" />
              </el-form-item>
              <el-form-item label="相似度阈值">
                <el-slider v-model="selectedNode.data.similarity_threshold" :min="0" :max="1" :step="0.1" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="selectedNode.data.output_var" placeholder="存储检索结果的变量名" />
              </el-form-item>
            </el-form>
          </template>
          
          <el-button type="danger" size="small" @click="deleteSelectedNode" style="width: 100%; margin-top: 10px">
            删除节点
          </el-button>
        </template>
        
        <template v-if="selectedEdge">
          <div class="panel-title">连线信息</div>
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
    
    <!-- 执行流程对话框 -->
    <el-dialog v-model="executeDialogVisible" title="执行" width="600px">
      <el-form label-width="100px">
        <el-form-item label="执行类型">
          <el-radio-group v-model="executeType">
            <el-radio label="agent">智能体</el-radio>
            <el-radio label="workflow">工作流</el-radio>
            <el-radio label="dialog_flow">对话流</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <template v-if="executeType === 'agent'">
          <el-form-item label="选择智能体">
            <el-select v-model="selectedExecuteAgentId" placeholder="请选择智能体" style="width: 100%">
              <el-option 
                v-for="agent in agents.filter(a => a.status === 'active')" 
                :key="agent.id" 
                :label="agent.name" 
                :value="agent.id" 
              />
            </el-select>
          </el-form-item>
        </template>
        
        <template v-if="executeType === 'workflow'">
          <el-form-item label="选择工作流">
            <el-select v-model="selectedExecuteWorkflowId" placeholder="请选择工作流" style="width: 100%">
              <el-option 
                v-for="workflow in workflows.filter(w => w.status === 'active')" 
                :key="workflow.id" 
                :label="workflow.name" 
                :value="workflow.id" 
              />
            </el-select>
          </el-form-item>
        </template>
        
        <template v-if="executeType === 'dialog_flow'">
          <el-form-item label="选择对话流">
            <el-select v-model="selectedExecuteDialogFlowId" placeholder="请选择对话流" style="width: 100%">
              <el-option 
                v-for="dialogFlow in dialogFlows.filter(df => df.status === 'active')" 
                :key="dialogFlow.id" 
                :label="dialogFlow.name" 
                :value="dialogFlow.id" 
              />
            </el-select>
          </el-form-item>
        </template>
        
        <el-form-item label="输入文本">
          <el-input v-model="executeText" type="textarea" :rows="4" placeholder="请输入要发送的文本" />
        </el-form-item>
        
        <el-form-item label="启用语音输出">
          <el-switch v-model="executeEnableTTS" />
        </el-form-item>
        
        <el-form-item label="温度" v-if="executeEnableTTS">
          <el-input-number v-model="executeTemperature" :min="0" :max="2" :step="0.1" />
        </el-form-item>
      </el-form>
      
      <el-divider v-if="executeResult" />
      
      <div v-if="executeResult" class="execute-result">
        <h4>执行结果：</h4>
        <el-alert 
          :title="executeResult.success ? '执行成功' : '执行失败'" 
          :type="executeResult.success ? 'success' : 'error'"
          :closable="false"
          class="mb-4"
        />
        <div v-if="executeResult.result" class="result-content">
          <h5>输出内容：</h5>
          <el-input 
            :model-value="formatExecuteResult(executeResult.result)" 
            type="textarea" 
            :rows="6" 
            readonly
          />
        </div>
        <div v-if="executeResult.audio_output" class="audio-output">
          <h5>语音输出：</h5>
          <audio controls :src="'data:audio/mp3;base64,' + executeResult.audio_output.audio_data" />
        </div>
      </div>
      
      <template #footer>
        <el-button @click="executeDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="doExecute" :loading="executing">执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { 
  ArrowLeft, Check, User, Share, Message, VideoPlay as Play, CircleCheck,
  // Dify 风格节点图标
  Document, Collection, DocumentChecked, EditPen, Filter, Link, List, Monitor, Cpu
} from '@element-plus/icons-vue'
import { ElMessage, ElEmpty, ElCard, ElTag, ElDialog, ElForm, ElFormItem, ElInput } from 'element-plus'
import { getAgents, getAgent, executeWorkflow, executeAgent, executeDialogFlow } from '@/api/agent'
import { getWorkflows, getWorkflow, createWorkflow, updateWorkflow } from '@/api/agent'
import { getDialogFlows, getDialogFlow } from '@/api/agent'
import { getModelList, getModelDetail } from '@/api/llm'

const router = useRouter()

const saving = ref(false)
const executing = ref(false)
const executeDialogVisible = ref(false)
const executeType = ref('agent')
const executeText = ref('')
const executeEnableTTS = ref(false)
const executeTemperature = ref(0.7)
const executeResult = ref(null)
const selectedExecuteAgentId = ref(null)
const selectedExecuteWorkflowId = ref(null)
const selectedExecuteDialogFlowId = ref(null)

const agents = ref([])
const workflows = ref([])
const dialogFlows = ref([])
const llms = ref([])

const nodes = ref([])
const edges = ref([])
const selectedNode = ref(null)
const selectedEdge = ref(null)

const currentAgentId = ref(null)
const currentDialogFlowId = ref(null)

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

const selectedAgent = ref(null)
const selectedWorkflow = ref(null)
const selectedDialogFlow = ref(null)
const selectedLLM = ref(null)

const nodeTypes = [
  // 基础节点
  { type: 'start', label: '开始', icon: Play, category: 'basic', next: ['input', 'agent', 'workflow', 'dialog_flow', 'llm', 'code', 'template', 'http', 'knowledge_retrieval'] },
  { type: 'end', label: '结束', icon: CircleCheck, category: 'basic', next: [] },
  { type: 'input', label: '输入', icon: Document, category: 'basic', next: ['agent', 'workflow', 'dialog_flow', 'llm', 'code', 'template', 'http', 'knowledge_retrieval'] },
  { type: 'output', label: '输出', icon: CircleCheck, category: 'basic', next: ['end'] },
  
  // 智能体相关
  { type: 'agent', label: '智能体', icon: User, category: 'agent', next: ['workflow', 'dialog_flow', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output'] },
  { type: 'workflow', label: '工作流', icon: Share, category: 'agent', next: ['agent', 'dialog_flow', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output'] },
  { type: 'dialog_flow', label: '对话流', icon: Message, category: 'agent', next: ['agent', 'workflow', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output'] },
  { type: 'llm', label: '大模型', icon: Monitor, category: 'agent', next: ['agent', 'workflow', 'dialog_flow', 'code', 'template', 'http', 'knowledge_retrieval', 'output'] },
  
  // Dify 风格节点 - 转换类
  { type: 'code', label: '代码执行', icon: Cpu, category: 'transform', next: ['agent', 'workflow', 'dialog_flow', 'llm', 'template', 'http', 'knowledge_retrieval', 'output'] },
  { type: 'template', label: '模板转换', icon: Document, category: 'transform', next: ['agent', 'workflow', 'dialog_flow', 'llm', 'code', 'http', 'knowledge_retrieval', 'output'] },
  { type: 'variable_aggregator', label: '变量聚合器', icon: Collection, category: 'transform', next: ['agent', 'workflow', 'dialog_flow', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output'] },
  { type: 'document_extractor', label: '文档提取器', icon: DocumentChecked, category: 'transform', next: ['agent', 'workflow', 'dialog_flow', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output'] },
  { type: 'variable_assigner', label: '变量赋值', icon: EditPen, category: 'transform', next: ['agent', 'workflow', 'dialog_flow', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output'] },
  { type: 'parameter_extractor', label: '参数提取器', icon: Filter, category: 'transform', next: ['agent', 'workflow', 'dialog_flow', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output'] },
  
  // Dify 风格节点 - 工具类
  { type: 'http', label: 'HTTP 请求', icon: Link, category: 'tool', next: ['agent', 'workflow', 'dialog_flow', 'llm', 'code', 'template', 'knowledge_retrieval', 'output'] },
  { type: 'list_operation', label: '列表操作', icon: List, category: 'tool', next: ['agent', 'workflow', 'dialog_flow', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output'] },
  { type: 'knowledge_retrieval', label: '知识检索', icon: Document, category: 'tool', next: ['agent', 'workflow', 'dialog_flow', 'llm', 'code', 'template', 'http', 'output'] }
]

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
    // 基础节点
    start: '▶️',
    end: '⏹️',
    // 智能体相关
    agent: '🤖',
    workflow: '🔄',
    dialog_flow: '💬',
    llm: '🧠',
    // Dify 风格节点 - 转换类
    code: '💻',
    template: '📄',
    variable_aggregator: '🔀',
    document_extractor: '📑',
    variable_assigner: '✏️',
    parameter_extractor: '🔍',
    // Dify 风格节点 - 工具类
    http: '🌐',
    list_operation: '📋'
  }
  return icons[type] || '📦'
}

const getNodeById = (id) => {
  return nodes.value.find(n => n.id === id)
}

const getNodeLLMName = (node) => {
  if (node.type !== 'llm' || !node.data.llm_id) return ''
  const llm = llms.value.find(l => l.id === node.data.llm_id)
  return llm ? `${llm.provider_name} - ${llm.model_name}` : ''
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
  router.push('/panel/agent/list')
}

const fetchAgents = async () => {
  try {
    const res = await getAgents({ limit: 1000 })
    agents.value = res.data?.items || res.data || []
  } catch (error) {
    console.error(error)
  }
}

const fetchWorkflows = async () => {
  try {
    const res = await getWorkflows({ limit: 1000 })
    workflows.value = res.data?.items || res.data || []
  } catch (error) {
    console.error(error)
  }
}

const fetchDialogFlows = async () => {
  try {
    const res = await getDialogFlows({ limit: 1000 })
    dialogFlows.value = res.data?.items || res.data || []
  } catch (error) {
    console.error(error)
  }
}

const fetchLLMs = async () => {
  try {
    const res = await getModelList({ page_size: 100, page: 1 })
    console.log('大模型列表响应:', res)
    llms.value = res.data?.items || res.data || []
    console.log('处理后的大模型列表:', llms.value)
  } catch (error) {
    console.error('获取大模型列表失败:', error)
  }
}

const saveFlow = async () => {
  saving.value = true
  try {
    const flowData = {
      nodes: nodes.value,
      edges: edges.value
    }
    
    if (currentAgentId.value) {
      // 保存到智能体配置中
      const response = await fetch(`/api/v1/agent/agents/${currentAgentId.value}/flow`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(flowData)
      })
      
      if (!response.ok) {
        throw new Error(`保存失败: ${response.statusText}`)
      }
      
      const result = await response.json()
      if (result.code === 200 || result.success) {
        ElMessage.success('流程图已保存到智能体配置中')
      } else {
        ElMessage.error(`保存失败: ${result.msg || result.message || '未知错误'}`)
      }
    } else {
      ElMessage.warning('请先选择智能体')
    }
  } catch (error) {
    ElMessage.error('保存失败')
    console.error('保存流程图错误:', error)
  } finally {
    saving.value = false
  }
}

const executeFlow = () => {
  executeDialogVisible.value = true
  executeType.value = 'agent'
  executeText.value = ''
  executeEnableTTS.value = false
  executeTemperature.value = 0.7
  executeResult.value = null
  selectedExecuteAgentId.value = currentAgentId.value || null
  selectedExecuteWorkflowId.value = null
  selectedExecuteDialogFlowId.value = null
}

const formatExecuteResult = (data) => {
  if (typeof data === 'string') {
    return data
  }
  if (typeof data === 'object') {
    try {
      return JSON.stringify(data, null, 2)
    } catch {
      return String(data)
    }
  }
  return String(data)
}

const doExecute = async () => {
  if (!executeText.value.trim()) {
    ElMessage.warning('请输入文本')
    return
  }
  
  let targetId = null
  
  if (executeType.value === 'agent') {
    if (!selectedExecuteAgentId.value) {
      ElMessage.warning('请选择智能体')
      return
    }
    targetId = selectedExecuteAgentId.value
  } else if (executeType.value === 'workflow') {
    if (!selectedExecuteWorkflowId.value) {
      ElMessage.warning('请选择工作流')
      return
    }
    targetId = selectedExecuteWorkflowId.value
  } else if (executeType.value === 'dialog_flow') {
    if (!selectedExecuteDialogFlowId.value) {
      ElMessage.warning('请选择对话流')
      return
    }
    targetId = selectedExecuteDialogFlowId.value
  }
  
  executing.value = true
  executeResult.value = null
  
  try {
    let res = null
    
    if (executeType.value === 'agent') {
      res = await executeAgent(targetId, {
        text: executeText.value,
        enable_tts: executeEnableTTS.value,
        parameters: {
          temperature: executeTemperature.value
        }
      })
    } else if (executeType.value === 'workflow') {
      res = await executeWorkflow(targetId, {
        text: executeText.value,
        input_text: executeText.value,
        parameters: {
          temperature: executeTemperature.value
        }
      })
    } else if (executeType.value === 'dialog_flow') {
      res = await executeDialogFlow(targetId, {
        text: executeText.value,
        input_text: executeText.value,
        parameters: {
          temperature: executeTemperature.value
        }
      })
    }
    
    if (res.data) {
      executeResult.value = res.data
      ElMessage.success('执行成功')
    } else {
      executeResult.value = {
        success: false,
        message: '没有返回数据'
      }
      ElMessage.error('执行失败')
    }
  } catch (error) {
    console.error('执行失败:', error)
    executeResult.value = {
      success: false,
      message: error.response?.data?.message || error.message || '执行失败'
    }
    ElMessage.error('执行失败')
  } finally {
    executing.value = false
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
    data: {
      label: nodeTypes.find(n => n.type === type)?.label || type
    }
  }
  nodes.value.push(newNode)
}

const onNodeClick = async (node) => {
  selectedEdge.value = null
  selectedNode.value = node
  
  // 重置选中的实体
  selectedAgent.value = null
  selectedWorkflow.value = null
  selectedDialogFlow.value = null
  selectedLLM.value = null
  
  // 根据节点类型加载对应的实体信息
  if (node.type === 'agent' && node.data.agent_id) {
    try {
      const res = await getAgent(node.data.agent_id)
      selectedAgent.value = res.data
    } catch (error) {
      console.error(error)
    }
  } else if (node.type === 'workflow' && node.data.workflowId) {
    try {
      const res = await getWorkflow(node.data.workflowId)
      selectedWorkflow.value = res.data
    } catch (error) {
      console.error(error)
    }
  } else if (node.type === 'dialog_flow' && node.data.dialogFlowId) {
    try {
      const res = await getDialogFlow(node.data.dialogFlowId)
      selectedDialogFlow.value = res.data
    } catch (error) {
      console.error(error)
    }
  } else if (node.type === 'llm' && node.data.llm_id) {
    try {
      const res = await getModelDetail(node.data.llm_id)
      selectedLLM.value = res.data
    } catch (error) {
      console.error(error)
    }
  }
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

const onInputPointMouseDown = (event, node) => {
  // 输入连接点的鼠标按下事件，目前不需要特殊处理
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
    const canvas = event.currentTarget
    const rect = canvas.getBoundingClientRect()
    currentMousePos.value = {
      x: event.clientX - rect.left + canvas.scrollLeft,
      y: event.clientY - rect.top + canvas.scrollTop
    }
  }
  
  if (draggingNode.value) {
    const canvas = event.currentTarget
    const rect = canvas.getBoundingClientRect()
    draggingNode.value.position = {
      x: event.clientX - rect.left + canvas.scrollLeft - dragOffset.value.x,
      y: event.clientY - rect.top + canvas.scrollTop - dragOffset.value.y
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
    selectedAgent.value = null
    selectedWorkflow.value = null
    selectedDialogFlow.value = null
    selectedLLM.value = null
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

const editAgent = (agentId) => {
  router.push(`/panel/agent/edit/${agentId}`)
}

const editWorkflow = (workflowId) => {
  router.push(`/panel/agent/workflows/edit/${workflowId}`)
}

const editDialogFlow = (dialogFlowId) => {
  router.push(`/panel/agent/dialog-flows/edit/${dialogFlowId}`)
}

const onLLMChange = async (llmId) => {
  if (llmId) {
    try {
      const res = await getModelDetail(llmId)
      selectedLLM.value = res.data
      // 更新节点标签为模型名称
      if (selectedNode.value) {
        selectedNode.value.data.label = res.data.model_name
      }
    } catch (error) {
      console.error(error)
      ElMessage.error('获取大模型详情失败')
    }
  } else {
    selectedLLM.value = null
  }
}

const updateNodeLabel = () => {
  // 节点标签已自动更新
  ElMessage.success('节点名称已更新')
}

const updateWorkflowSelection = async () => {
  const workflowId = selectedNode.value.data.workflowId
  if (workflowId) {
    try {
      const workflow = workflows.value.find(w => w.id === workflowId)
      if (workflow) {
        selectedWorkflow.value = workflow
        
        // 从工作流关联的智能体中获取大模型信息
        if (currentAgentId.value) {
          try {
            const agentRes = await getAgent(currentAgentId.value)
            if (agentRes.data && agentRes.data.llm_model_id) {
              // 获取大模型详情
              const llmRes = await getModelDetail(agentRes.data.llm_model_id)
              if (llmRes.data) {
                selectedLLM.value = llmRes.data
              }
            }
          } catch (error) {
            console.error('获取智能体大模型信息失败:', error)
          }
        }
        
        ElMessage.success('工作流选择成功')
      }
    } catch (error) {
      console.error('获取工作流详情失败:', error)
      ElMessage.error('获取工作流详情失败')
    }
  }
}

const updateDialogFlowSelection = async () => {
  const dialogFlowId = selectedNode.value.data.dialogFlowId
  if (dialogFlowId) {
    try {
      const dialogFlow = dialogFlows.value.find(df => df.id === dialogFlowId)
      if (dialogFlow) {
        selectedDialogFlow.value = dialogFlow
        ElMessage.success('对话流选择成功')
      }
    } catch (error) {
      console.error('获取对话流详情失败:', error)
      ElMessage.error('获取对话流详情失败')
    }
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(async () => {
  fetchAgents()
  fetchWorkflows()
  fetchDialogFlows()
  fetchLLMs()
  
  const route = router.currentRoute.value
  const agentId = route.query.agent_id
  
  if (agentId) {
    currentAgentId.value = parseInt(agentId)
    
    try {
      // 加载智能体信息
      const agentRes = await getAgent(agentId)
      if (agentRes.data && agentRes.data.config) {
        // 从智能体配置中加载流程图数据
        const flowData = agentRes.data.config?.flow_data
        if (flowData) {
          nodes.value = flowData.nodes || []
          edges.value = flowData.edges || []
        }
      }
    } catch (error) {
      console.error('加载智能体流程图失败:', error)
    }
  }
  
  if (nodes.value.length === 0) {
    nodes.value = [
      {
        id: 'start-1',
        type: 'start',
        position: { x: 100, y: 200 },
        data: { label: '开始' }
      },
      {
        id: 'agent-1',
        type: 'agent',
        position: { x: 300, y: 200 },
        data: { label: '智能体' }
      },
      {
        id: 'end-1',
        type: 'end',
        position: { x: 500, y: 200 },
        data: { label: '结束' }
      }
    ]
    
    edges.value = [
      {
        id: 'edge-1',
        source: 'start-1',
        target: 'agent-1'
      },
      {
        id: 'edge-2',
        source: 'agent-1',
        target: 'end-1'
      }
    ]
  }
})
</script>

<style scoped>
.agent-flow {
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
  max-height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
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

.agent-edge {
  fill: none;
  stroke: #409eff;
  stroke-width: 2;
  cursor: pointer;
  pointer-events: stroke;
  transition: stroke-width 0.2s;
}

.agent-edge:hover,
.agent-edge.selected {
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

.agent-node {
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

.agent-node:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.agent-node.selected {
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

.agent-node {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: #667eea;
}

.workflow-node {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: #fff;
  border-color: #4facfe;
}

.dialog_flow-node {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: #fff;
  border-color: #f093fb;
}

.llm-node {
  background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
  color: #333;
  border-color: #a8edea;
}

/* Dify 风格节点 - 转换类 */
.code-node {
  background: linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%);
  color: #fff;
  border-color: #2c3e50;
}

.template-node {
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
  color: #333;
  border-color: #fcb69f;
}

.variable_aggregator-node {
  background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%);
  color: #333;
  border-color: #8ec5fc;
}

.document_extractor-node {
  background: linear-gradient(135deg, #d4fc79 0%, #96e6a1 100%);
  color: #333;
  border-color: #96e6a1;
}

.variable_assigner-node {
  background: linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%);
  color: #333;
  border-color: #a1c4fd;
}

.parameter_extractor-node {
  background: linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%);
  color: #333;
  border-color: #fbc2eb;
}

/* Dify 风格节点 - 工具类 */
.http-node {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: #667eea;
}

.list_operation-node {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: #fff;
  border-color: #11998e;
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
  font-size: 16px;
}

.node-label {
  font-size: 14px;
  font-weight: 500;
}

.node-subtitle {
  font-size: 11px;
  opacity: 0.8;
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

.agent-info,
.workflow-info,
.dialog-flow-info {
  line-height: 1.8;
  font-size: 13px;
}

.agent-info p,
.workflow-info p,
.dialog-flow-info p {
  margin: 8px 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.execute-result {
  margin-top: 16px;
}

.execute-result h4 {
  margin-bottom: 12px;
  font-size: 16px;
  font-weight: 600;
}

.execute-result h5 {
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
}

.result-content {
  margin-bottom: 16px;
}

.audio-output {
  margin-top: 16px;
}

.audio-output audio {
  width: 100%;
  margin-top: 8px;
}

.mb-4 {
  margin-bottom: 16px;
}
</style>
