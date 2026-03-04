<template>
  <div class="usage-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>使用记录</span>
        </div>
      </template>

      <!-- 搜索表单 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="服务类型">
          <el-select v-model="searchForm.service_type" placeholder="请选择服务类型" clearable>
            <el-option label="全部" :value="null" />
            <el-option label="文本生成" value="text_generation" />
            <el-option label="图像生成" value="image_generation" />
            <el-option label="语音合成" value="tts" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchData">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 数据表格 -->
      <el-table :data="tableData" style="width: 100%" v-loading="loading" border>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="customer_id" label="客户ID" width="100" />
        <el-table-column prop="service_type" label="服务类型" width="120">
          <template #default="{ row }">
            {{ getServiceTypeLabel(row.service_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="duration_seconds" label="使用时长(秒)" width="120" />
        <el-table-column prop="characters_count" label="字符数" width="100" />
        <el-table-column prop="api_cost" label="API成本" width="100">
          <template #default="{ row }">
            ${{ row.api_cost }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="详情" width="100">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleViewDetail(row)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchData"
        @current-change="fetchData"
      />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="使用记录详情" width="600px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="ID">{{ currentDetail.id }}</el-descriptions-item>
        <el-descriptions-item label="客户ID">{{ currentDetail.customer_id }}</el-descriptions-item>
        <el-descriptions-item label="会话ID">{{ currentDetail.session_id }}</el-descriptions-item>
        <el-descriptions-item label="服务类型">
          {{ getServiceTypeLabel(currentDetail.service_type) }}
        </el-descriptions-item>
        <el-descriptions-item label="使用时长">{{ currentDetail.duration_seconds }} 秒</el-descriptions-item>
        <el-descriptions-item label="字符数">{{ currentDetail.characters_count }}</el-descriptions-item>
        <el-descriptions-item label="API成本">${{ currentDetail.api_cost }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDateTime(currentDetail.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="详情">
          <pre>{{ JSON.stringify(currentDetail.details, null, 2) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { getUsageLogs } from '@/api/customer'

// 响应式数据
const loading = ref(false)
const tableData = ref([])
const detailDialogVisible = ref(false)
const currentDetail = ref({})

const searchForm = reactive({
  service_type: null
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 方法
const fetchData = async () => {
  loading.value = true
  try {
    const res = await getUsageLogs({
      page: pagination.page,
      page_size: pagination.pageSize,
      service_type: searchForm.service_type
    })

    if (res.success) {
      tableData.value = res.data.items || []
      pagination.total = res.data.total || 0
    } else {
      ElMessage.error(res.msg || '获取数据失败')
    }
  } catch (e) {
    ElMessage.error('获取数据失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  searchForm.service_type = null
  fetchData()
}

const handleViewDetail = (row) => {
  currentDetail.value = row
  detailDialogVisible.value = true
}

const getServiceTypeLabel = (type) => {
  const labels = {
    text_generation: '文本生成',
    image_generation: '图像生成',
    tts: '语音合成',
    translation: '翻译'
  }
  return labels[type] || type
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.usage-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
}

pre {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  max-height: 300px;
  overflow-y: auto;
}
</style>
