<template>
  <div class="langgraph-edit-page">
    <div class="page-header">
      <el-button @click="goBack" :icon="ArrowLeft">返回</el-button>
      <h2>{{ workflow?.name || 'LangGraph 工作流编辑' }}</h2>
    </div>

    <LangGraphEditor
      v-if="workflowId"
      :workflow-id="workflowId"
      :title="workflow?.name"
      :initial-nodes="initialNodes"
      :initial-edges="initialEdges"
      @save="onSave"
      @execute="onExecute"
    />

    <el-empty v-else description="请先选择工作流" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getWorkflow } from '@/api/agent'
import LangGraphEditor from '@/components/LangGraphEditor.vue'

const route = useRoute()
const router = useRouter()

const workflowId = ref(null)
const workflow = ref(null)
const initialNodes = ref([])
const initialEdges = ref([])

const goBack = () => {
  router.push('/panel/agent/workflows')
}

const fetchWorkflow = async () => {
  try {
    const id = route.params.id
    workflowId.value = id
    
    const res = await getWorkflow(id)
    workflow.value = res.data
    
    if (res.data.definition) {
      const def = res.data.definition
      
      if (def.nodes) {
        initialNodes.value = def.nodes.map(node => ({
          id: node.id,
          type: 'custom',
          position: node.position || { x: 100, y: 100 },
          data: {
            type: node.type,
            label: node.data?.label || node.type,
            description: node.data?.description,
            ...node.data
          }
        }))
      }
      
      if (def.edges) {
        initialEdges.value = def.edges.map(edge => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          animated: true,
          style: { stroke: '#409EFF' },
          enabled: edge.enabled !== false,
          priority: edge.priority || 0,
          condition: edge.condition || '',
          description: edge.description || ''
        }))
      }
    }
  } catch (error) {
    ElMessage.error('获取工作流失败')
    console.error(error)
  }
}

const onSave = (data) => {
  console.log('Workflow saved:', data)
}

const onExecute = (result) => {
  console.log('Workflow executed:', result)
}

onMounted(() => {
  fetchWorkflow()
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
