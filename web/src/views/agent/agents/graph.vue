<template>
  <div class="agent-graph-editor">
    <LangGraphEditor 
      :title="`${agentName} - 结构图`"
      :agentId="agentId"
      :initialNodes="initialNodes"
      :initialEdges="initialEdges"
      @save="handleSave"
      @execute="handleExecute"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import LangGraphEditor from '@/components/LangGraphEditor.vue'
import { getAgent, getAgentGraph, updateAgentGraph } from '@/api/agent'

const route = useRoute()
const agentId = computed(() => route.params.id)
const agentName = ref('智能体')
const initialNodes = ref([])
const initialEdges = ref([])

const fetchAgent = async () => {
  try {
    const res = await getAgent(agentId.value)
    if (res.data) {
      agentName.value = res.data.name
    }
  } catch (error) {
    console.error('获取智能体信息失败', error)
  }
}

const fetchAgentGraph = async () => {
  try {
    console.log('=== 开始获取智能体结构图 ===')
    console.log('agentId:', agentId.value)
    
    const res = await getAgentGraph(agentId.value)
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
    console.error('获取智能体结构图失败', error)
  }
}

const handleSave = async ({ nodes, edges }) => {
  try {
    console.log('保存智能体结构图:', { nodes, edges })
    
    const graphData = { 
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges))
    }
    
    console.log('转换后的 graphData:', graphData)
    
    await updateAgentGraph(agentId.value, graphData)
    ElMessage.success('结构图保存成功')
  } catch (error) {
    ElMessage.error('结构图保存失败: ' + (error.message || error))
    console.error('保存失败详情:', error)
  }
}

const handleExecute = async (result) => {
  console.log('执行结果:', result)
  // 注意：不要在这里显示成功消息，LangGraphEditor 组件内部已经显示了
}

onMounted(() => {
  fetchAgent()
  fetchAgentGraph()
})
</script>

<style scoped>
.agent-graph-editor {
  height: 100%;
}
</style>


