<template>
  <div class="api-keys">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>API密钥管理（调试版）</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增密钥</el-button>
        </div>
      </template>

      <!-- 表格保持不变 -->
      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="provider_name" label="厂商" width="120" />
        <el-table-column prop="api_id" label="API ID (LLM)" min-width="150" />
        <el-table-column label="语音密钥" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.has_voice_credentials ? 'success' : 'info'" size="small">
              {{ row.has_voice_credentials ? '已配置' : '未配置' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link :icon="Edit" @click="handleEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑密钥（调试版）' : '新增密钥'" width="800px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="160px">
        <!-- 调试信息 -->
        <el-alert title="调试模式" type="info" :closable="false" style="margin-bottom: 20px">
          <div>编辑模式: {{ isEdit }}</div>
          <div>API Key ID: {{ form.id }}</div>
        </el-alert>

        <el-divider content-position="left">语音服务密钥（测试区域）</el-divider>

        <el-form-item label="API ID (语音)">
          <el-input v-model="form.api_id_voice" placeholder="语音服务的API ID" />
        </el-form-item>

        <el-form-item label="App Key (语音)">
          <el-input
            v-model="form.app_key_voice"
            type="password"
            placeholder="输入新的App Key"
            show-password
          />
          <div class="text-gray text-xs mt-1">
            当前值: {{ form.app_key_voice || '空' }}
          </div>
        </el-form-item>

        <el-form-item label="API Secret (语音)">
          <el-input
            v-model="form.api_secret_voice"
            type="password"
            placeholder="输入新的API Secret"
            show-password
          />
          <div class="text-gray text-xs mt-1">
            当前值: {{ form.api_secret_voice || '空' }}
          </div>
        </el-form-item>

        <el-form-item label="端点URL (语音)">
          <el-input v-model="form.endpoint_url_voice" placeholder="输入端点URL" />
          <div class="text-gray text-xs mt-1">
            当前值: {{ form.endpoint_url_voice || '空' }}
          </div>
        </el-form-item>

        <!-- 调试信息 -->
        <el-divider content-position="left">提交前检查</el-divider>

        <el-descriptions :column="1" border>
          <el-descriptions-item label="form.api_id_voice">
            {{ form.api_id_voice || '空' }}
          </el-descriptions-item>
          <el-descriptions-item label="form.app_key_voice">
            {{ form.app_key_voice || '空' }}
          </el-descriptions-item>
          <el-descriptions-item label="form.api_secret_voice">
            {{ form.api_secret_voice || '空' }}
          </el-descriptions-item>
          <el-descriptions-item label="form.endpoint_url_voice">
            {{ form.endpoint_url_voice || '空' }}
          </el-descriptions-item>
        </el-descriptions>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button @click="debugSubmit">调试提交（查看日志）</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 调试日志弹窗 -->
    <el-dialog v-model="debugLogVisible" title="调试日志" width="800px">
      <pre style="max-height: 400px; overflow-y: auto; background: #f5f5f5; padding: 10px; font-size: 12px;">{{ debugLog }}</pre>
      <template #footer>
        <el-button type="primary" @click="copyDebugLog">复制日志</el-button>
        <el-button @click="debugLogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getProviderList,
  getApiKeyList,
  updateApiKey
} from '@/api/llm'

const loading = ref(false)
const tableData = ref([])
const providerList = ref([])
const dialogVisible = ref(false)
const debugLogVisible = ref(false)
const debugLog = ref('')
const formRef = ref()
const isEdit = ref(false)

const form = reactive({
  id: null,
  api_id_voice: '',
  app_key_voice: '',
  api_secret_voice: '',
  endpoint_url_voice: ''
})

const rules = {}

const fetchData = async () => {
  loading.value = true
  try {
    const { data } = await getApiKeyList({ page: 1, page_size: 10 })
    tableData.value = data.items || []
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
    api_id_voice: '',
    app_key_voice: '',
    api_secret_voice: '',
    endpoint_url_voice: ''
  })
  isEdit.value = false
  dialogVisible.value = true
}

const handleEdit = (row) => {
  console.log('===== handleEdit 被调用 =====')
  console.log('原始行数据:', JSON.parse(JSON.stringify(row)))

  Object.assign(form, {
    ...row,
    app_key_voice: row.app_key_voice || '',
    api_secret_voice: row.api_secret_voice || ''
  })

  console.log('表单数据（编辑后）:', JSON.parse(JSON.stringify(form)))
  console.log('===========================\n')

  isEdit.value = true
  dialogVisible.value = true
}

const debugSubmit = async () => {
  console.log('\n===== debugSubmit 调试提交 =====')
  const logs = []

  try {
    // 1. 检查表单数据
    logs.push('【步骤1】检查表单数据')
    logs.push(`form.api_id_voice: ${form.api_id_voice || '空'}`)
    logs.push(`form.app_key_voice: ${form.app_key_voice || '空'}`)
    logs.push(`form.api_secret_voice: ${form.api_secret_voice || '空'}`)
    logs.push(`form.endpoint_url_voice: ${form.endpoint_url_voice || '空'}`)

    // 2. 构造updateData
    const updateData = { ...form }
    logs.push('\n【步骤2】构造updateData')
    logs.push(JSON.stringify(updateData, null, 2))

    // 3. 检查哪些字段会被删除
    logs.push('\n【步骤3】检查字段删除逻辑')
    const willDelete = []

    if (!updateData.app_key_voice || updateData.app_key_voice.includes('****')) {
      willDelete.push('app_key_voice')
      delete updateData.app_key_voice
    }

    if (!updateData.api_secret_voice || updateData.api_secret_voice.includes('****')) {
      willDelete.push('api_secret_voice')
      delete updateData.api_secret_voice
    }

    if (willDelete.length > 0) {
      logs.push(`将被删除的字段: ${willDelete.join(', ')}`)
    } else {
      logs.push('没有字段会被删除')
    }

    // 4. 最终提交的数据
    logs.push('\n【步骤4】最终提交的updateData')
    logs.push(JSON.stringify(updateData, null, 2))

    // 5. 发送请求
    logs.push('\n【步骤5】发送API请求')
    logs.push(`URL: /api/v1/llm/api-keys/${form.id}`)
    logs.push('Method: PUT')

    const response = await updateApiKey(form.id, updateData)
    logs.push('\n【步骤6】API响应')
    logs.push(JSON.stringify(response.data, null, 2))

    // 6. 检查响应数据
    if (response.data) {
      logs.push('\n【步骤7】检查响应数据')
      logs.push(`api_id_voice: ${response.data.api_id_voice || 'NULL'}`)
      logs.push(`app_key_voice: ${response.data.app_key_voice || 'NULL'}`)
      logs.push(`has_voice_credentials: ${response.data.has_voice_credentials}`)
    }

    logs.push('\n✅ 调试完成')
    ElMessage.success('调试完成，请查看日志')

  } catch (error) {
    logs.push('\n❌ 错误信息')
    logs.push(error.toString())
    if (error.response) {
      logs.push('Response data:')
      logs.push(JSON.stringify(error.response.data, null, 2))
    }
    ElMessage.error('调试失败，请查看日志')
  }

  debugLog.value = logs.join('\n')
  debugLogVisible.value = true

  console.log('\n===== debugSubmit 完成 =====')
}

const submit = async () => {
  await formRef.value.validate()
  try {
    if (isEdit.value) {
      const updateData = { ...form }

      // 检查语音密钥
      if (!updateData.app_key_voice || updateData.app_key_voice.includes('****')) {
        delete updateData.app_key_voice
      }
      if (!updateData.api_secret_voice || updateData.api_secret_voice.includes('****')) {
        delete updateData.api_secret_voice
      }

      console.log('===== submit 发送更新请求 =====')
      console.log('updateData:', updateData)

      const response = await updateApiKey(form.id, updateData)
      console.log('API响应:', response.data)

      ElMessage.success('更新成功')
      dialogVisible.value = false
      fetchData()
    }
  } catch (error) {
    console.error('更新失败:', error)
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const copyDebugLog = () => {
  navigator.clipboard.writeText(debugLog.value)
  ElMessage.success('日志已复制')
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
