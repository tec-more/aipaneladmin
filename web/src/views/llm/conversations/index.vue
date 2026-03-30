<template>
  <div class="conversations">
    <el-card shadow="never">
      <template #header>
        <span>对话记录</span>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" :model="searchForm" class="search-form mb-4">
        <el-form-item label="客户ID">
          <el-input v-model.number="searchForm.customer_id" placeholder="客户ID" clearable style="width: 150px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择" clearable style="width: 120px">
            <el-option label="活跃" value="active" />
            <el-option label="已结束" value="ended" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="fetchData">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="conversation_id" label="对话ID" min-width="200" show-overflow-tooltip />
        <el-table-column prop="customer_id" label="客户ID" width="100" align="center" />
        <el-table-column prop="model_id" label="模型ID" width="100" align="center" />
        <el-table-column label="消息数" width="100" align="center">
          <template #default="{ row }">
            {{ row.message_count }} 条
          </template>
        </el-table-column>
        <el-table-column label="Token统计" width="200" align="center">
          <template #default="{ row }">
            <div>总计: {{ formatNumber(row.total_tokens) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="成本" width="120" align="center">
          <template #default="{ row }">
            ¥{{ row.total_cost?.toFixed(4) || '0.0000' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '活跃' : '已结束' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link :icon="View" @click="handleViewDetail(row)">详情</el-button>
            <el-button type="success" link :icon="DataAnalysis" @click="handleViewSummary(row)">统计</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 对话详情弹窗 -->
    <el-dialog v-model="detailDialogVisible" title="对话详情" width="800px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="对话ID" :span="2">
          {{ currentConversation.conversation_id }}
        </el-descriptions-item>
        <el-descriptions-item label="客户ID">
          {{ currentConversation.customer_id }}
        </el-descriptions-item>
        <el-descriptions-item label="模型">
          {{ currentConversation.model?.model_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="总Token数">
          {{ formatNumber(currentConversation.total_tokens) }}
        </el-descriptions-item>
        <el-descriptions-item label="总成本">
          ¥{{ currentConversation.total_cost?.toFixed(4) || '0.0000' }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="currentConversation.status === 'active' ? 'success' : 'info'">
            {{ currentConversation.status === 'active' ? '活跃' : '已结束' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ currentConversation.created_at }}
        </el-descriptions-item>
      </el-descriptions>

      <el-divider>对话消息</el-divider>

      <div class="messages-container">
        <div v-if="!currentConversation.messages || currentConversation.messages.length === 0" class="empty-messages">
          暂无消息记录
        </div>
        <div v-else class="messages-list">
          <div
            v-for="(msg, index) in currentConversation.messages"
            :key="index"
            :class="['message-item', `message-${msg.role}`]"
          >
            <div class="message-header">
              <el-tag :type="msg.role === 'user' ? 'primary' : msg.role === 'assistant' ? 'success' : 'warning'" size="small">
                {{ getRoleName(msg.role) }}
              </el-tag>
            </div>
            <div class="message-content">{{ msg.content }}</div>
          </div>
        </div>
      </div>

      <!-- 使用记录 -->
      <el-divider>使用记录</el-divider>

      <el-table v-loading="usageLoading" :data="usageList" border stripe size="small" max-height="300">
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column label="Token统计" width="200" align="center">
          <template #default="{ row }">
            <div>输入: {{ formatNumber(row.prompt_tokens) }}</div>
            <div>输出: {{ formatNumber(row.completion_tokens) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="total_tokens" label="总计" width="100" align="center">
          <template #default="{ row }">
            {{ formatNumber(row.total_tokens) }}
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="成本(元)" width="120" align="center">
          <template #default="{ row }">
            ¥{{ row.cost?.toFixed(4) || '0.0000' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="180" />
      </el-table>
    </el-dialog>

    <!-- 统计汇总弹窗 -->
    <el-dialog v-model="summaryDialogVisible" title="对话统计汇总" width="600px">
      <el-descriptions v-if="summary" :column="2" border>
        <el-descriptions-item label="对话ID" :span="2">
          {{ summary.conversation_id }}
        </el-descriptions-item>
        <el-descriptions-item label="消息数">
          {{ summary.message_count }} 条
        </el-descriptions-item>
        <el-descriptions-item label="请求数">
          {{ summary.total_requests }} 次
        </el-descriptions-item>
        <el-descriptions-item label="总输入Token">
          {{ formatNumber(summary.total_prompt_tokens) }}
        </el-descriptions-item>
        <el-descriptions-item label="总输出Token">
          {{ formatNumber(summary.total_completion_tokens) }}
        </el-descriptions-item>
        <el-descriptions-item label="总Token数">
          {{ formatNumber(summary.total_tokens) }}
        </el-descriptions-item>
        <el-descriptions-item label="总成本">
          ¥{{ summary.total_cost?.toFixed(4) || '0.0000' }}
        </el-descriptions-item>
        <el-descriptions-item label="平均Token/请求">
          {{ formatNumber(summary.average_tokens_per_request) }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="summary.status === 'active' ? 'success' : 'info'">
            {{ summary.status === 'active' ? '活跃' : '已结束' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, View, DataAnalysis } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getConversationList,
  getConversationDetail,
  getConversationUsage,
  getConversationSummary
} from '@/api/llm'

const loading = ref(false)
const usageLoading = ref(false)
const tableData = ref([])
const usageList = ref([])
const detailDialogVisible = ref(false)
const summaryDialogVisible = ref(false)
const currentConversation = ref({})
const summary = ref(null)

const searchForm = reactive({
  customer_id: null,
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const fetchData = async () => {
  loading.value = true
  try {
    const { data } = await getConversationList({
      ...searchForm,
      page: pagination.page,
      page_size: pagination.pageSize
    })
    tableData.value = data.items || []
    pagination.total = data.total || 0
  } catch (error) {
    ElMessage.error('获取对话列表失败')
  } finally {
    loading.value = false
  }
}

const handleViewDetail = async (row) => {
  try {
    const { data } = await getConversationDetail(row.id)
    currentConversation.value = data
    detailDialogVisible.value = true

    // 加载使用记录
    loadUsageData(row.id)
  } catch (error) {
    ElMessage.error('获取对话详情失败')
  }
}

const loadUsageData = async (conversationId) => {
  usageLoading.value = true
  try {
    const { data } = await getConversationUsage(conversationId, { page: 1, page_size: 50 })
    usageList.value = data.items || []
  } catch (error) {
    console.error('获取使用记录失败', error)
  } finally {
    usageLoading.value = false
  }
}

const handleViewSummary = async (row) => {
  try {
    const { data } = await getConversationSummary(row.id)
    summary.value = data
    summaryDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取统计汇总失败')
  }
}

const handleReset = () => {
  searchForm.customer_id = null
  searchForm.status = ''
  fetchData()
}

const formatNumber = (num) => {
  if (!num) return '0'
  return num.toLocaleString()
}

const getRoleName = (role) => {
  const roleMap = {
    system: '系统',
    user: '用户',
    assistant: '助手'
  }
  return roleMap[role] || role
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.conversations {
  padding: 20px;
}

.search-form {
  margin-bottom: 16px;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.messages-container {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
}

.empty-messages {
  text-align: center;
  color: #909399;
  padding: 40px 0;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-item {
  padding: 10px;
  border-radius: 4px;
  background-color: #f5f7fa;
}

.message-item.message-user {
  background-color: #ecf5ff;
}

.message-item.message-assistant {
  background-color: #f0f9ff;
}

.message-item.message-system {
  background-color: #fef0f0;
}

.message-header {
  margin-bottom: 6px;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.mb-4 {
  margin-bottom: 16px;
}
</style>
