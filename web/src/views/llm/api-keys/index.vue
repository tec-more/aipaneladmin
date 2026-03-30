<template>
  <div class="api-keys">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>API密钥管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增密钥</el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" :model="searchForm" class="search-form mb-4">
        <el-form-item label="厂商">
          <el-select v-model="searchForm.provider_id" placeholder="请选择" clearable style="width: 150px">
            <el-option v-for="provider in providerList" :key="provider.id" :label="provider.name" :value="provider.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择" clearable style="width: 120px">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="fetchData">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="provider_name" label="厂商" width="120" />
        <el-table-column prop="name" label="密钥名称" min-width="150" />
        <el-table-column prop="api_key" label="API Key" min-width="200">
          <template #default="{ row }">
            <el-tag>{{ row.api_key }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="endpoint_url" label="端点URL" min-width="200" show-overflow-tooltip />
        <el-table-column label="配额使用" width="180" align="center">
          <template #default="{ row }">
            <div class="quota-info">
              <el-progress
                :percentage="getQuotaPercentage(row)"
                :color="getQuotaColor(row)"
                :stroke-width="8"
              />
              <div class="quota-text">
                {{ row.used_quota }} / {{ row.max_quota }}
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="可用性" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_available ? 'success' : 'danger'">
              {{ row.is_available ? '可用' : '不可用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_used_at" label="最后使用" width="180" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="280" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link :icon="Edit" @click="handleEdit(row)">编辑</el-button>
            <el-button type="success" link :icon="RefreshRight" @click="handleResetQuota(row)">重置</el-button>
            <el-button type="warning" link :icon="Connection" @click="handleTest(row)">测试</el-button>
            <el-button type="danger" link :icon="Delete" @click="handleDelete(row)">删除</el-button>
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

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑密钥' : '新增密钥'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="所属厂商" prop="provider_id">
          <el-select v-model="form.provider_id" placeholder="请选择厂商" style="width: 100%">
            <el-option v-for="provider in providerList" :key="provider.id" :label="provider.name" :value="provider.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="密钥名称" prop="name">
          <el-input v-model="form.name" placeholder="如：OpenAI主账号" />
        </el-form-item>
        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="form.api_key" type="password" placeholder="sk-..." show-password />
        </el-form-item>
        <el-form-item label="API Secret">
          <el-input v-model="form.api_secret" type="password" placeholder="某些厂商需要" show-password />
        </el-form-item>
        <el-form-item label="端点URL">
          <el-input v-model="form.endpoint_url" placeholder="自定义端点，留空使用默认" />
        </el-form-item>
        <el-form-item label="每日配额限制" prop="max_quota">
          <el-input-number v-model="form.max_quota" :min="0" :step="10000" style="width: 100%" />
          <div class="text-gray text-xs">tokens/天，0表示不限制</div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 测试结果弹窗 -->
    <el-dialog v-model="testDialogVisible" title="测试结果" width="500px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="状态">
          <el-tag :type="testResult.available ? 'success' : 'danger'">
            {{ testResult.available ? '可用' : '不可用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item v-if="!testResult.available" label="原因">
          {{ testResult.reason || '未知错误' }}
        </el-descriptions-item>
        <el-descriptions-item label="剩余配额">
          {{ testResult.remaining_quota || 0 }} tokens
        </el-descriptions-item>
        <el-descriptions-item v-if="testResult.message" label="提示">
          {{ testResult.message }}
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="testDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus, Edit, Delete, Search, Refresh, RefreshRight, Connection } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getProviderList,
  getApiKeyList,
  createApiKey,
  updateApiKey,
  deleteApiKey,
  resetApiKeyQuota,
  testApiKey
} from '@/api/llm'

const loading = ref(false)
const tableData = ref([])
const providerList = ref([])
const dialogVisible = ref(false)
const testDialogVisible = ref(false)
const formRef = ref()
const isEdit = ref(false)

const searchForm = reactive({
  provider_id: null,
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const form = reactive({
  id: null,
  provider_id: null,
  name: '',
  api_key: '',
  api_secret: '',
  endpoint_url: '',
  max_quota: 100000,
  description: ''
})

const testResult = reactive({
  available: false,
  reason: '',
  remaining_quota: 0,
  message: ''
})

const rules = {
  provider_id: [{ required: true, message: '请选择厂商', trigger: 'change' }],
  name: [{ required: true, message: '请输入密钥名称', trigger: 'blur' }],
  api_key: [{ required: true, message: '请输入API Key', trigger: 'blur' }]
}

const fetchData = async () => {
  loading.value = true
  try {
    const { data } = await getApiKeyList({
      ...searchForm,
      page: pagination.page,
      page_size: pagination.pageSize
    })
    tableData.value = data.items || []
    pagination.total = data.total || 0
  } catch (error) {
    ElMessage.error('获取密钥列表失败')
  } finally {
    loading.value = false
  }
}

const fetchProviders = async () => {
  try {
    const { data } = await getProviderList({ page: 1, page_size: 100 })
    providerList.value = data.items || []
  } catch (error) {
    ElMessage.error('获取厂商列表失败')
  }
}

const handleAdd = () => {
  Object.assign(form, {
    id: null,
    provider_id: null,
    name: '',
    api_key: '',
    api_secret: '',
    endpoint_url: '',
    max_quota: 100000,
    description: ''
  })
  isEdit.value = false
  dialogVisible.value = true
}

const handleEdit = (row) => {
  // 不直接复制api_key和api_secret，编辑时重新填写
  Object.assign(form, {
    ...row,
    api_key: '',
    api_secret: ''
  })
  isEdit.value = true
  dialogVisible.value = true
}

const submit = async () => {
  await formRef.value.validate()
  try {
    if (isEdit.value) {
      // 如果没填密钥，只更新其他字段
      const updateData = { ...form }
      if (!updateData.api_key) delete updateData.api_key
      if (!updateData.api_secret) delete updateData.api_secret
      await updateApiKey(form.id, updateData)
      ElMessage.success('更新成功')
    } else {
      await createApiKey(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定要删除密钥"${row.name}"吗？`, '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await deleteApiKey(row.id)
      ElMessage.success('删除成功')
      fetchData()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  })
}

const handleResetQuota = (row) => {
  ElMessageBox.confirm('确定要重置此密钥的配额吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await resetApiKeyQuota(row.id)
      ElMessage.success('重置成功')
      fetchData()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '重置失败')
    }
  })
}

const handleTest = async (row) => {
  try {
    const { data } = await testApiKey(row.id)
    Object.assign(testResult, data)
    testDialogVisible.value = true
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '测试失败')
  }
}

const handleReset = () => {
  searchForm.provider_id = null
  searchForm.status = ''
  fetchData()
}

const getQuotaPercentage = (row) => {
  if (row.max_quota === 0) return 0
  return Math.min(100, Math.round((row.used_quota / row.max_quota) * 100))
}

const getQuotaColor = (row) => {
  const percentage = getQuotaPercentage(row)
  if (percentage >= 90) return '#f56c6c'
  if (percentage >= 70) return '#e6a23c'
  return '#67c23a'
}

onMounted(() => {
  fetchProviders()
  fetchData()
})
</script>

<style scoped>
.api-keys {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 16px;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.quota-info {
  padding: 0 10px;
}

.quota-text {
  font-size: 12px;
  color: #606266;
  margin-top: 4px;
}

.text-gray {
  color: #909399;
}

.text-xs {
  font-size: 12px;
}

.mb-4 {
  margin-bottom: 16px;
}
</style>
