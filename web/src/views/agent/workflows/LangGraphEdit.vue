<template>
  <div class="langgraph-edit-page">
    <LangGraphEditor
      v-if="workflowId"
      :workflow-id="workflowId"
      :title="workflowName"
      :initial-nodes="initialNodes"
      :initial-edges="initialEdges"
      @save="handleSave"
      @execute="handleExecute"
    />

    <el-empty v-else description="请先选择工作流" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getWorkflow, getWorkflowGraph, updateWorkflowGraph } from '@/api/agent'
import LangGraphEditor from '@/components/LangGraphEditor.vue'

const route = useRoute()
const router = useRouter()

const workflowId = computed(() => route.params.id)
const workflowName = ref('工作流')
const initialNodes = ref([])
const initialEdges = ref([])

const goBack = () => {
  router.push('/panel/agent/workflows')
}

const fetchWorkflow = async () => {
  try {
    const res = await getWorkflow(workflowId.value)
    if (res.data) {
      workflowName.value = res.data.name
    }
  } catch (error) {
    console.error('获取工作流信息失败', error)
  }
}

const fetchWorkflowGraph = async () => {
  try {
    console.log('=== 开始获取工作流结构图 ===')
    console.log('workflowId:', workflowId.value)
    
    const res = await getWorkflowGraph(workflowId.value)
    console.log('API 返回结果:', res)
    console.log('res.data:', res.data)
    console.log('res.data.graph_definition:', res.data?.graph_definition)
    
    if (res.data?.graph_definition) {
      console.log('graph_definition.nodes:', res.data.graph_definition.nodes)
      console.log('graph_definition.edges:', res.data.graph_definition.edges)
      
      initialNodes.value = res.data.graph_definition.nodes || []
      initialEdges.value = (res.data.graph_definition.edges || []).map(edge => ({
        ...edge,
        enabled: edge.enabled !== false,
        priority: edge.priority || 0,
        condition: edge.condition || '',
        description: edge.description || ''
      }))
      
      console.log('设置后的 initialNodes:', initialNodes.value)
      console.log('设置后的 initialEdges:', initialEdges.value)
    } else {
      console.log('没有找到 graph_definition，初始化空数组')
      initialNodes.value = []
      initialEdges.value = []
    }
  } catch (error) {
    console.error('获取工作流结构图失败', error)
  }
}

const handleSave = async ({ nodes, edges }) => {
  try {
    console.log('保存工作流结构图:', { nodes, edges })
    
    const graphData = { 
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges))
    }
    
    console.log('转换后的 graphData:', graphData)
    
    await updateWorkflowGraph(workflowId.value, graphData)
    ElMessage.success('结构图保存成功')
  } catch (error) {
    ElMessage.error('结构图保存失败: ' + (error.message || error))
    console.error('保存失败详情:', error)
  }
}

const handleExecute = async (result) => {
  console.log('执行结果:', result)
}

onMounted(() => {
  fetchWorkflow()
  fetchWorkflowGraph()
})
</script>

<style scoped>
.langgraph-edit-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
</style>


