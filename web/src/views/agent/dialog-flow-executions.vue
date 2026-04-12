<template>
  <div class="execution-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>对话流执行记录</span>
        </div>
      </template>
      
      <el-form :inline="true" :model="searchForm" class="mb-4">
        <el-form-item label="对话流">
          <el-select v-model="searchForm.dialog_flow_id" placeholder="请选择对话流" clearable filterable>
            <el-option v-for="df in dialogFlows" :key="df.id" :label="df.name" :value="df.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态" clearable>
            <el-option label="运行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetSearch">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
      
      <el-table :data="executions" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="dialog_flow_name" label="对话流" min-width="150">
          <template #default="{ row }">
            {{ getDialogFlowName(row.dialog_flow_id) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusName(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.completed_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="viewDetail(row)">
              <el-icon><View /></el-icon>
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="mt-4">
        <el-pagination
          v-model:current-page="pageInfo.currentPage"
          v-model:page-size="pageInfo.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="pageInfo.total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailDialogVisible" title="执行详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="对话流">{{ currentExecution?.dialog_flow_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentExecution?.status)">{{ getStatusName(currentExecution?.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ formatDate(currentExecution?.started_at) }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatDate(currentExecution?.completed_at) }}</el-descriptions-item>
      </el-descriptions>
      <el-divider />
      <el-form label-width="100px">
        <el-form-item label="输入数据">
          <el-input :model-value="formatJson(currentExecution?.input_data)" type="textarea" :rows="4" readonly />
        </el-form-item>
        <el-form-item label="输出数据">
          <el-input :model-value="formatJson(currentExecution?.output_data)" type="textarea" :rows="4" readonly />
        </el-form-item>
        <el-form-item label="执行路径">
          <el-input :model-value="formatJson(currentExecution?.execution_path)" type="textarea" :rows="4" readonly />
        </el-form-item>
        <el-form-item label="错误信息" v-if="currentExecution?.error_message">
          <el-input :model-value="currentExecution?.error_message" type="textarea" :rows="3" readonly />
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, View } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getDialogFlowExecutions, getDialogFlows } from '@/api/agent'

const loading = ref(false)
const executions = ref([])
const dialogFlows = ref([])

const searchForm = reactive({
  dialog_flow_id: null,
  status: ''
})

const pageInfo = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

const detailDialogVisible = ref(false)
const currentExecution = ref(null)

const statusMap = {
  running: '运行中',
  completed: '已完成',
  failed: '失败'
}

const getStatusName = (status) => statusMap[status] || status
const getStatusType = (status) => {
  const map = { running: 'warning', completed: 'success', failed: 'danger' }
  return map[status] || ''
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

const formatJson = (data) => {
  if (!data) return ''
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

const getDialogFlowName = (dialogFlowId) => {
  const df = dialogFlows.value.find(d => d.id === dialogFlowId)
  return df ? df.name : '-'
}

const fetchDialogFlows = async () => {
  try {
    const res = await getDialogFlows({ limit: 1000 })
    dialogFlows.value = res.data?.items || res.data || []
  } catch (error) {
    console.error(error)
  }
}

const fetchExecutions = async () => {
  loading.value = true
  try {
    const res = await getDialogFlowExecutions({
      skip: (pageInfo.currentPage - 1) * pageInfo.pageSize,
      limit: pageInfo.pageSize,
      ...searchForm
    })
    if (res.data) {
      executions.value = res.data.items || res.data
      pageInfo.total = res.data.total || executions.value.length
    }
  } catch (error) {
    ElMessage.error('获取执行记录失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pageInfo.currentPage = 1
  fetchExecutions()
}

const resetSearch = () => {
  searchForm.dialog_flow_id = null
  searchForm.status = ''
  handleSearch()
}

const handleSizeChange = (size) => {
  pageInfo.pageSize = size
  fetchExecutions()
}

const handleCurrentChange = (current) => {
  pageInfo.currentPage = current
  fetchExecutions()
}

const viewDetail = (row) => {
  currentExecution.value = row
  detailDialogVisible.value = true
}

onMounted(() => {
  fetchDialogFlows()
  fetchExecutions()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.mb-4 {
  margin-bottom: 16px;
}
.mt-4 {
  margin-top: 16px;
}
</style>
