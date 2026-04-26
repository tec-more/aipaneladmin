<template>
  <div class="workflow-editor">
    <div class="toolbar">
      <span class="workflow-name">{{ workflow?.name || '工作流编辑' }}</span>
      <el-tag :type="getStatusType(workflow?.status)" size="small">{{ getStatusName(workflow?.status) }}</el-tag>
      <div class="toolbar-right">
        <el-button @click="handleImportGraph">
          <el-icon><Upload /></el-icon>
          导入
        </el-button>
        <el-button @click="handleExportGraph">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button type="primary" @click="saveWorkflow" :loading="saving">
          <el-icon><Check /></el-icon>
          保存
        </el-button>
        <el-button 
          type="warning" 
          @click="publishWorkflow" 
          v-if="workflow?.status !== 'active'"
        >
          <el-icon><Check /></el-icon>
          发布
        </el-button>
        <el-button type="success" @click="executeWorkflowDialog">
          <el-icon><VideoPlay /></el-icon>
          执行
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
            <el-form-item label="描述">
              <el-input v-model="nodeConfig.description" type="textarea" :rows="2" @change="updateNodeData" placeholder="节点功能描述" />
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
            
            <!-- 智能体节点配置 -->
            <template v-if="selectedNode.type === 'agent'">
              <el-divider content-position="left">智能体配置</el-divider>
              <el-form-item label="选择智能体">
                <el-select v-model="nodeConfig.agent_id" placeholder="请选择" @change="updateNodeData">
                  <el-option v-for="agent in agents" :key="agent.id" :label="agent.name" :value="agent.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="提示词">
                <el-input v-model="nodeConfig.prompt" type="textarea" :rows="4" @change="updateNodeData" placeholder="为智能体设置提示词" />
              </el-form-item>
              <el-form-item label="等待输入">
                <el-switch v-model="nodeConfig.wait_for_input" @change="updateNodeData" />
              </el-form-item>
            </template>
            
            <!-- 技能节点配置 -->
            <template v-if="selectedNode.type === 'skill'">
              <el-divider content-position="left">技能配置</el-divider>
              <el-form-item label="选择技能">
                <el-select v-model="nodeConfig.skill_id" placeholder="请选择" @change="updateNodeData">
                  <el-option v-for="skill in skills" :key="skill.id" :label="skill.name" :value="skill.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="提示词">
                <el-input v-model="nodeConfig.prompt" type="textarea" :rows="4" @change="updateNodeData" placeholder="为技能设置提示词" />
              </el-form-item>
              <el-form-item label="技能参数">
                <el-input v-model="nodeConfig.skill_params" type="textarea" :rows="2" @change="updateNodeData" placeholder="JSON格式参数" />
              </el-form-item>
            </template>
            
            <!-- 大模型节点配置 -->
            <template v-if="selectedNode.type === 'llm'">
              <el-divider content-position="left">大模型配置</el-divider>
              <el-form-item label="选择模型">
                <el-select v-model="nodeConfig.model_id" placeholder="请选择" @change="updateNodeData">
                  <el-option 
                    v-for="model in models" 
                    :key="model.id" 
                    :label="`${model.provider_name} - ${model.model_name}`" 
                    :value="model.id" 
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="提示词">
                <el-input v-model="nodeConfig.prompt" type="textarea" :rows="4" @change="updateNodeData" placeholder="设置提示词" />
              </el-form-item>
              <el-form-item label="温度">
                <el-slider v-model="nodeConfig.temperature" :min="0" :max="2" :step="0.1" @change="updateNodeData" />
              </el-form-item>
              <el-form-item label="最大Token">
                <el-input-number v-model="nodeConfig.max_tokens" :min="1" :max="4096" @change="updateNodeData" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="nodeConfig.output_var" placeholder="例如: llm_output" @change="updateNodeData" />
              </el-form-item>
            </template>
            
            <!-- 条件判断节点配置 -->
            <template v-if="selectedNode.type === 'decision'">
              <el-divider content-position="left">条件配置</el-divider>
              <el-form-item label="条件表达式">
                <el-input v-model="nodeConfig.condition" type="textarea" :rows="3" @change="updateNodeData" placeholder="如: input.age > 18" />
              </el-form-item>
              <el-form-item label="条件描述">
                <el-input v-model="nodeConfig.condition_desc" @change="updateNodeData" placeholder="条件的简要描述" />
              </el-form-item>
            </template>
            
            <!-- 循环节点配置 -->
            <template v-if="selectedNode.type === 'loop'">
              <el-divider content-position="left">循环配置</el-divider>
              <el-form-item label="循环条件">
                <el-input v-model="nodeConfig.condition" type="textarea" :rows="2" @change="updateNodeData" placeholder="如: index < 10" />
              </el-form-item>
              <el-form-item label="最大次数">
                <el-input-number v-model="nodeConfig.loop_count" :min="1" :max="100" @change="updateNodeData" />
              </el-form-item>
              <el-form-item label="循环变量">
                <el-input v-model="nodeConfig.loop_variable" @change="updateNodeData" placeholder="如: i" />
              </el-form-item>
            </template>
            
            <!-- 迭代节点配置 -->
            <template v-if="selectedNode.type === 'iteration'">
              <el-divider content-position="left">迭代配置</el-divider>
              <el-form-item label="迭代集合">
                <el-input v-model="nodeConfig.iteration_collection" @change="updateNodeData" placeholder="如: items" />
              </el-form-item>
              <el-form-item label="迭代变量">
                <el-input v-model="nodeConfig.iteration_variable" @change="updateNodeData" placeholder="如: item" />
              </el-form-item>
              <el-form-item label="迭代条件">
                <el-input v-model="nodeConfig.iteration_condition" type="textarea" :rows="2" @change="updateNodeData" placeholder="如: item.status === 'active'" />
              </el-form-item>
            </template>
            
            <!-- 输入节点配置 -->
            <template v-if="selectedNode.type === 'input'">
              <el-divider content-position="left">输入配置</el-divider>
              <el-form-item label="输入类型">
                <el-select v-model="nodeConfig.input_type" @change="updateNodeData">
                  <el-option label="文本" value="text" />
                  <el-option label="文件" value="file" />
                  <el-option label="表单" value="form" />
                </el-select>
              </el-form-item>
              <el-form-item label="输入提示">
                <el-input v-model="nodeConfig.input_placeholder" @change="updateNodeData" placeholder="用户输入提示" />
              </el-form-item>
            </template>
            
            <!-- 等待节点配置 -->
            <template v-if="selectedNode.type === 'wait'">
              <el-divider content-position="left">等待配置</el-divider>
              <el-form-item label="等待时长">
                <el-input-number v-model="nodeConfig.wait_seconds" :min="1" :max="3600" @change="updateNodeData" /> 秒
              </el-form-item>
              <el-form-item label="等待提示">
                <el-input v-model="nodeConfig.wait_message" @change="updateNodeData" placeholder="等待时显示的消息" />
              </el-form-item>
            </template>
            
            <!-- HTTP节点配置 -->
            <template v-if="selectedNode.type === 'http'">
              <el-divider content-position="left">HTTP配置</el-divider>
              <el-form-item label="请求方法">
                <el-select v-model="nodeConfig.http_method" @change="updateNodeData">
                  <el-option label="GET" value="GET" />
                  <el-option label="POST" value="POST" />
                  <el-option label="PUT" value="PUT" />
                  <el-option label="DELETE" value="DELETE" />
                </el-select>
              </el-form-item>
              <el-form-item label="请求URL">
                <el-input v-model="nodeConfig.http_url" @change="updateNodeData" placeholder="https://api.example.com" />
              </el-form-item>
              <el-form-item label="请求头">
                <el-input v-model="nodeConfig.http_headers" type="textarea" :rows="2" @change="updateNodeData" placeholder="JSON格式" />
              </el-form-item>
              <el-form-item label="请求体">
                <el-input v-model="nodeConfig.http_body" type="textarea" :rows="3" @change="updateNodeData" placeholder="JSON格式" />
              </el-form-item>
            </template>
            
            <!-- 代码节点配置 -->
            <template v-if="selectedNode.type === 'code'">
              <el-divider content-position="left">代码配置</el-divider>
              <el-form-item label="代码语言">
                <el-select v-model="nodeConfig.code_language" @change="updateNodeData">
                  <el-option label="JavaScript" value="javascript" />
                  <el-option label="Python" value="python" />
                </el-select>
              </el-form-item>
              <el-form-item label="代码内容">
                <el-input v-model="nodeConfig.code_content" type="textarea" :rows="6" @change="updateNodeData" placeholder="// 输入代码" />
              </el-form-item>
            </template>
            
            <!-- 模板节点配置 -->
            <template v-if="selectedNode.type === 'template'">
              <el-divider content-position="left">模板配置</el-divider>
              <el-form-item label="模板内容">
                <el-input v-model="nodeConfig.template" type="textarea" :rows="4" @change="updateNodeData" placeholder="使用 {{variable}} 引用变量" />
              </el-form-item>
            </template>
            
            <!-- 变量聚合器节点配置 -->
            <template v-if="selectedNode.type === 'variable_aggregator'">
              <el-divider content-position="left">变量聚合器配置</el-divider>
              <el-form-item label="输入变量">
                <el-input v-model="nodeConfig.input_vars" type="textarea" :rows="3" @change="updateNodeData" placeholder="每行一个变量名" />
              </el-form-item>
              <el-form-item label="输出变量">
                <el-input v-model="nodeConfig.output_var" @change="updateNodeData" placeholder="聚合后的变量名" />
              </el-form-item>
            </template>
            
            <!-- 文档提取器节点配置 -->
            <template v-if="selectedNode.type === 'document_extractor'">
              <el-divider content-position="left">文档提取器配置</el-divider>
              <el-form-item label="文档变量">
                <el-input v-model="nodeConfig.document_var" @change="updateNodeData" placeholder="文档内容变量名" />
              </el-form-item>
              <el-form-item label="提取规则">
                <el-input v-model="nodeConfig.extract_rules" type="textarea" :rows="3" @change="updateNodeData" placeholder="提取规则配置" />
              </el-form-item>
            </template>
            
            <!-- 变量赋值节点配置 -->
            <template v-if="selectedNode.type === 'variable_assigner'">
              <el-divider content-position="left">变量赋值配置</el-divider>
              <el-form-item label="变量名">
                <el-input v-model="nodeConfig.var_name" @change="updateNodeData" placeholder="变量名称" />
              </el-form-item>
              <el-form-item label="变量值">
                <el-input v-model="nodeConfig.var_value" type="textarea" :rows="2" @change="updateNodeData" placeholder="变量值或表达式" />
              </el-form-item>
            </template>
            
            <!-- 参数提取器节点配置 -->
            <template v-if="selectedNode.type === 'parameter_extractor'">
              <el-divider content-position="left">参数提取器配置</el-divider>
              <el-form-item label="输入文本">
                <el-input v-model="nodeConfig.input_text" @change="updateNodeData" placeholder="输入文本变量名" />
              </el-form-item>
              <el-form-item label="提取参数">
                <el-input v-model="nodeConfig.parameters" type="textarea" :rows="3" @change="updateNodeData" placeholder="每行一个参数名" />
              </el-form-item>
            </template>
            
            <!-- 列表操作节点配置 -->
            <template v-if="selectedNode.type === 'list_operation'">
              <el-divider content-position="left">列表操作配置</el-divider>
              <el-form-item label="操作类型">
                <el-select v-model="nodeConfig.operation" @change="updateNodeData">
                  <el-option label="过滤" value="filter" />
                  <el-option label="映射" value="map" />
                  <el-option label="排序" value="sort" />
                  <el-option label="去重" value="unique" />
                </el-select>
              </el-form-item>
              <el-form-item label="输入列表">
                <el-input v-model="nodeConfig.input_list" @change="updateNodeData" placeholder="变量名" />
              </el-form-item>
            </template>
            
            <!-- 知识检索节点配置 -->
            <template v-if="selectedNode.type === 'knowledge_retrieval'">
              <el-divider content-position="left">知识检索配置</el-divider>
              <el-form-item label="知识库">
                <el-select v-model="nodeConfig.knowledge_base" @change="updateNodeData">
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
            
            <!-- LangChain Agent 节点配置 -->
            <template v-if="selectedNode.type === 'langchain_agent'">
              <el-divider content-position="left">LangChain Agent 配置</el-divider>
              <el-form-item label="Agent类型">
                <el-select v-model="nodeConfig.agent_type" @change="updateNodeData" style="width: 100%">
                  <el-option label="Zero Shot ReAct" value="zero_shot_react_description" />
                  <el-option label="OpenAI Functions" value="openai_functions" />
                  <el-option label="Conversational ReAct" value="conversational_react" />
                  <el-option label="Chat Zero Shot" value="chat_zero_shot_react" />
                </el-select>
              </el-form-item>
              <el-form-item label="记忆类型">
                <el-select v-model="nodeConfig.memory_type" @change="updateNodeData" style="width: 100%">
                  <el-option label="Conversation Buffer" value="buffer" />
                  <el-option label="Conversation Summary" value="summary" />
                </el-select>
              </el-form-item>
              <el-form-item label="选择技能">
                <el-select v-model="nodeConfig.skill_ids" multiple @change="updateNodeData" style="width: 100%" placeholder="选择技能作为Tools">
                  <el-option v-for="skill in skills" :key="skill.id" :label="skill.name" :value="skill.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="大模型">
                <el-select v-model="nodeConfig.llm_id" @change="updateNodeData" style="width: 100%" placeholder="请选择">
                  <el-option v-for="model in llms" :key="model.id" :label="model.name" :value="model.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="输入文本">
                <el-input v-model="nodeConfig.input_text" type="textarea" :rows="2" @change="updateNodeData" placeholder="可使用 {{变量}} 引用" />
              </el-form-item>
              <el-form-item label="详细日志">
                <el-switch v-model="nodeConfig.verbose" @change="updateNodeData" />
              </el-form-item>
            </template>
            
            <!-- LangChain Chain 节点配置 -->
            <template v-if="selectedNode.type === 'langchain_chain'">
              <el-divider content-position="left">LangChain Chain 配置</el-divider>
              <el-form-item label="提示词模板">
                <el-input v-model="nodeConfig.prompt_template" type="textarea" :rows="4" @change="updateNodeData" placeholder="例如: 请将以下文本翻译成法语: {input}" />
              </el-form-item>
              <el-form-item label="输入变量">
                <el-input v-model="nodeConfig.input_variables" @change="updateNodeData" placeholder="用逗号分隔，例如: input, context" />
              </el-form-item>
              <el-form-item label="大模型">
                <el-select v-model="nodeConfig.llm_id" @change="updateNodeData" style="width: 100%" placeholder="请选择">
                  <el-option v-for="model in llms" :key="model.id" :label="model.name" :value="model.id" />
                </el-select>
              </el-form-item>
            </template>
            
            <!-- LangChain RAG 节点配置 -->
            <template v-if="selectedNode.type === 'langchain_rag'">
              <el-divider content-position="left">LangChain RAG 配置</el-divider>
              <el-form-item label="查询问题">
                <el-input v-model="nodeConfig.query" type="textarea" :rows="2" @change="updateNodeData" placeholder="可使用 {{变量}} 引用" />
              </el-form-item>
              <el-form-item label="Chain类型">
                <el-select v-model="nodeConfig.chain_type" @change="updateNodeData" style="width: 100%">
                  <el-option label="Stuff" value="stuff" />
                  <el-option label="Map Reduce" value="map_reduce" />
                  <el-option label="Refine" value="refine" />
                  <el-option label="Map Rerank" value="map_rerank" />
                </el-select>
              </el-form-item>
              <el-form-item label="向量库路径">
                <el-input v-model="nodeConfig.vector_store_path" @change="updateNodeData" placeholder="./vector_stores/xxx" />
              </el-form-item>
              <el-form-item label="大模型">
                <el-select v-model="nodeConfig.llm_id" @change="updateNodeData" style="width: 100%" placeholder="请选择">
                  <el-option v-for="model in llms" :key="model.id" :label="model.name" :value="model.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="返回源文档">
                <el-switch v-model="nodeConfig.return_source_documents" @change="updateNodeData" />
              </el-form-item>
            </template>
            
            <!-- 输出节点配置 -->
            <template v-if="selectedNode.type === 'output'">
              <el-divider content-position="left">输出配置</el-divider>
              <el-form-item label="输出类型">
                <el-select v-model="nodeConfig.output_type" @change="updateNodeData">
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
            
            <!-- 开始和结束节点 -->
            <template v-if="selectedNode.type === 'start' || selectedNode.type === 'end'">
              <el-divider content-position="left">节点信息</el-divider>
              <el-form-item label="节点类型">
                <el-tag>{{ selectedNode.type === 'start' ? '开始节点' : '结束节点' }}</el-tag>
              </el-form-item>
            </template>
          </el-form>
          
          <el-button type="danger" size="small" @click="deleteSelectedNode" style="width: 100%">
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

    <el-dialog v-model="executeDialogVisible" title="执行工作流" width="900px" class="wechat-style-dialog">
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
            v-model="executeInput"
            type="textarea"
            :rows="3"
            placeholder="请输入..."
            class="input-textarea"
          />
          <div class="input-actions">
            <el-button @click="clearDialogHistory" :disabled="dialogHistory.length === 0">清空历史</el-button>
            <el-button @click="executeDialogVisible = false">关闭</el-button>
            <el-button type="primary" @click="doExecute" :loading="executing">执行</el-button>
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
  ArrowLeft, Check, VideoPlay, User, Tools, Share, VideoPlay as Play, CircleCheck, Monitor, Upload, Download,
  // Dify 风格节点图标
  Document, Collection, DocumentChecked, EditPen, Filter, Link, List, Cpu
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getWorkflow, updateWorkflow, executeWorkflow } from '@/api/agent'
import { getAgents, getSkills } from '@/api/agent'
import { getModelList } from '@/api/llm'

const route = useRoute()
const router = useRouter()

const workflowId = route.params.id
const workflow = ref(null)
const saving = ref(false)
const agents = ref([])
const skills = ref([])
const models = ref([])

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
  description: '',
  agent_id: null,
  skill_id: null,
  model_id: null,
  condition: '',
  loop_count: 1,
  // 输入节点配置
  input_type: 'text',
  input_placeholder: '',
  // 知识检索节点配置
  knowledge_base: 'default',
  query: '',
  top_k: 5,
  similarity_threshold: 0.7,
  // 输出节点配置
  output_var: '',
  output_type: 'text',
  output_content: ''
})

const nodeTypes = [
  // 基础节点
  { type: 'start', label: '开始', icon: Play, category: 'basic', next: ['input', 'agent', 'skill', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'decision', 'loop', 'iteration'] },
  { type: 'end', label: '结束', icon: CircleCheck, category: 'basic', next: [] },
  { type: 'input', label: '输入', icon: EditPen, category: 'basic', next: ['agent', 'skill', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'decision', 'loop', 'iteration'] },
  { type: 'output', label: '输出', icon: Monitor, category: 'basic', next: ['end'] },
  
  // 智能体相关
  { type: 'agent', label: '智能体', icon: User, category: 'agent', next: ['skill', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  { type: 'skill', label: '技能', icon: Tools, category: 'agent', next: ['agent', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  { type: 'llm', label: '大模型', icon: Monitor, category: 'agent', next: ['skill', 'code', 'template', 'http', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  { type: 'decision', label: '条件判断', icon: Share, category: 'agent', next: ['agent', 'skill', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  { type: 'loop', label: '循环', icon: Share, category: 'agent', next: ['agent', 'skill', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'decision', 'loop', 'iteration'] },
  { type: 'iteration', label: '迭代', icon: Share, category: 'agent', next: ['agent', 'skill', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'decision', 'loop', 'iteration'] },
  
  // Dify 风格节点 - 转换类
  { type: 'code', label: '代码执行', icon: Cpu, category: 'transform', next: ['agent', 'skill', 'llm', 'template', 'http', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  { type: 'template', label: '模板转换', icon: Document, category: 'transform', next: ['agent', 'skill', 'llm', 'code', 'http', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  { type: 'variable_aggregator', label: '变量聚合器', icon: Collection, category: 'transform', next: ['agent', 'skill', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  { type: 'document_extractor', label: '文档提取器', icon: DocumentChecked, category: 'transform', next: ['agent', 'skill', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  { type: 'variable_assigner', label: '变量赋值', icon: EditPen, category: 'transform', next: ['agent', 'skill', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  { type: 'parameter_extractor', label: '参数提取器', icon: Filter, category: 'transform', next: ['agent', 'skill', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  
  // Dify 风格节点 - 工具类
  { type: 'http', label: 'HTTP 请求', icon: Link, category: 'tool', next: ['agent', 'skill', 'llm', 'code', 'template', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  { type: 'list_operation', label: '列表操作', icon: List, category: 'tool', next: ['agent', 'skill', 'llm', 'code', 'template', 'http', 'knowledge_retrieval', 'output', 'decision', 'loop', 'iteration'] },
  { type: 'knowledge_retrieval', label: '知识检索', icon: Document, category: 'tool', next: ['agent', 'skill', 'llm', 'code', 'template', 'http', 'output', 'decision', 'loop', 'iteration'] }
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
    agent: '🤖',
    skill: '⚡',
    llm: '🧠',
    decision: '🔀',
    loop: '🔁',
    branch: '🌿'
  }
  return icons[type] || '📦'
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
  router.push('/panel/agent/workflows')
}

const fetchWorkflow = async () => {
  try {
    const res = await getWorkflow(workflowId)
    workflow.value = res.data
    if (res.data.definition) {
      nodes.value = res.data.definition.nodes || []
      edges.value = res.data.definition.edges || []
    }
  } catch (error) {
    ElMessage.error('获取工作流失败')
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

const saveWorkflow = async () => {
  saving.value = true
  try {
    await updateWorkflow(workflowId, {
      definition: { nodes: nodes.value, edges: edges.value }
    })
    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  } finally {
    saving.value = false
  }
}

const publishWorkflow = async () => {
  saving.value = true
  try {
    await updateWorkflow(workflowId, {
      status: 'active',
      definition: { nodes: nodes.value, edges: edges.value }
    })
    workflow.value.status = 'active'
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
    data: { label: nodeTypes.find(n => n.type === type)?.label || type }
  }
  nodes.value.push(newNode)
}

const onNodeClick = (node) => {
  selectedEdge.value = null
  selectedNode.value = node
  nodeConfig.label = node.data.label || ''
  nodeConfig.description = node.data.description || ''
  nodeConfig.agent_id = node.data.agent_id || null
  nodeConfig.skill_id = node.data.skill_id || null
  nodeConfig.model_id = node.data.model_id || null
  nodeConfig.condition = node.data.condition || ''
  nodeConfig.loop_count = node.data.loop_count || 1
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
      description: nodeConfig.description,
      agent_id: nodeConfig.agent_id,
      skill_id: nodeConfig.skill_id,
      model_id: nodeConfig.model_id,
      condition: nodeConfig.condition,
      loop_count: nodeConfig.loop_count,
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

const clearDialogHistory = () => {
  dialogHistory.value = []
  currentInput.value = ''
  latestResponse.value = ''
  ElMessage.success('对话历史已清空')
}

const executeWorkflowDialog = () => {
  executeInput.value = ''
  executeResult.value = ''
  executeDialogVisible.value = true
}

const doExecute = async () => {
  executing.value = true
  try {
    const input = JSON.parse(executeInput.value)
    const res = await executeWorkflow(workflowId, input)
    executeResult.value = JSON.stringify(res.data, null, 2)
    ElMessage.success('执行成功')
  } catch (error) {
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
    name: workflow.value?.name || 'workflow',
    description: workflow.value?.description || ''
  }
  const blob = new Blob([JSON.stringify(graphData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${workflow.value?.name || 'workflow'}-${Date.now()}.json`
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
  fetchWorkflow()
  fetchAgents()
  fetchSkills()
  fetchModels()
})
</script>

<style scoped>
.workflow-editor {
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

.workflow-name {
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

.agent-node {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: #667eea;
}

.skill-node {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: #fff;
  border-color: #f093fb;
}

.decision-node {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: #fff;
  border-color: #4facfe;
}

.llm-node {
  background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%);
  color: #fff;
  border-color: #a18cd1;
}

.loop-node {
  background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%);
  color: #fff;
  border-color: #ff9a9e;
}

.branch-node {
  background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
  color: #fff;
  border-color: #a8edea;
}

.knowledge_retrieval-node {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: #667eea;
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
  padding: 20px;
  overflow: hidden;
}

/* 聊天消息 */
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