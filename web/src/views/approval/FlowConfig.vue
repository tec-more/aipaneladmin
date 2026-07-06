<template>
  <div class="flow-config">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>审批流程配置</span>
          <el-button type="primary" @click="handleCreate">新建流程</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="name" label="流程名称" min-width="150" />
        <el-table-column prop="code" label="流程编码" width="150" />
        <el-table-column prop="business_type" label="业务类型" width="120">
          <template #default="{ row }">{{ row.business_type || '通用' }}</template>
        </el-table-column>
        <el-table-column prop="is_system" label="系统预设" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_system ? 'warning' : 'info'" size="small">
              {{ row.is_system ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="(val) => handleToggleStatus(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button
              v-if="!row.is_system"
              type="danger" link @click="handleDelete(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 编辑/新建对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px" destroy-on-close>
      <el-form :model="formData" label-width="100px" ref="formRef">
        <el-form-item label="流程名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入流程名称" />
        </el-form-item>
        <el-form-item label="流程编码" prop="code">
          <el-input
            v-model="formData.code"
            placeholder="请输入流程编码（唯一）"
            :disabled="Boolean(formData.id)"
          />
        </el-form-item>
        <el-form-item label="业务类型">
          <el-input v-model="formData.business_type" placeholder="如：purchase_order, expense, leave" />
        </el-form-item>
        <el-form-item label="流程描述">
          <el-input v-model="formData.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="formData.is_active" />
        </el-form-item>

        <!-- 表单配置 -->
        <el-divider>表单配置</el-divider>
        <div v-for="(field, index) in formData.form_config" :key="index" class="field-item">
          <el-input v-model="field.label" placeholder="字段标签" style="width: 140px" />
          <el-input v-model="field.field" placeholder="字段名" style="width: 140px; margin: 0 8px" />
          <el-select v-model="field.type" placeholder="类型" style="width: 120px">
            <el-option label="文本" value="text" />
            <el-option label="数字" value="number" />
            <el-option label="文本域" value="textarea" />
            <el-option label="日期" value="date" />
            <el-option label="下拉" value="select" />
          </el-select>
          <el-button type="danger" link @click="removeField(index)" style="margin-left: 8px">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-button @click="addField" type="primary" link>
          <el-icon><Plus /></el-icon> 添加字段
        </el-button>

        <!-- 流程配置(JSON) -->
        <el-divider>流程节点配置（JSON）</el-divider>
        <el-input
          v-model="flowConfigText"
          type="textarea"
          :rows="8"
          placeholder="流程配置JSON"
        />
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getFlowList, createFlow, updateFlow, deleteFlow, toggleFlowStatus } from '@/api/approval'

const loading = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogMode = ref('create')
const flowConfigText = ref('{}')
const formRef = ref()

const pagination = reactive({ page: 1, page_size: 10, total: 0 })
const formData = reactive({
  id: null,
  name: '',
  code: '',
  business_type: '',
  description: '',
  is_active: true,
  form_config: [],
  flow_config: {}
})

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getFlowList(pagination)
    if (res.code === 0 || res.code === 200 || res.success) {
      tableData.value = res.data.items || []
      pagination.total = res.data.total || 0
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  Object.assign(formData, {
    id: null, name: '', code: '', business_type: '', description: '',
    is_active: true, form_config: [], flow_config: {}
  })
  flowConfigText.value = '{}'
}

const handleCreate = () => {
  resetForm()
  dialogMode.value = 'create'
  dialogTitle.value = '新建流程'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  resetForm()
  Object.assign(formData, {
    id: row.id, name: row.name, code: row.code, business_type: row.business_type || '',
    description: row.description || '', is_active: row.is_active,
    form_config: row.form_config || [], flow_config: row.flow_config || {}
  })
  flowConfigText.value = JSON.stringify(row.flow_config || {}, null, 2)
  dialogMode.value = 'edit'
  dialogTitle.value = '编辑流程'
  dialogVisible.value = true
}

const addField = () => {
  formData.form_config.push({ label: '', field: '', type: 'text' })
}

const removeField = (index) => {
  formData.form_config.splice(index, 1)
}

const handleToggleStatus = async (row, val) => {
  try {
    await toggleFlowStatus(row.id, val)
    ElMessage.success('状态已更新')
  } catch (e) {
    row.is_active = !val
    console.error(e)
  }
}

const submitForm = async () => {
  try {
    formData.flow_config = JSON.parse(flowConfigText.value)
  } catch (e) {
    ElMessage.error('流程配置JSON格式错误')
    return
  }

  try {
    if (dialogMode.value === 'create') {
      const res = await createFlow({ ...formData })
      if (res.code === 0 || res.code === 200 || res.success) {
        ElMessage.success('创建成功')
      }
    } else {
      const { id, ...updateData } = formData
      const res = await updateFlow(id, updateData)
      if (res.code === 0 || res.code === 200 || res.success) {
        ElMessage.success('更新成功')
      }
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    console.error(e)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除流程「${row.name}」吗？`, '提示', { type: 'warning' })
    const res = await deleteFlow(row.id)
    if (res.code === 0 || res.code === 200 || res.success) {
      ElMessage.success('删除成功')
      fetchData()
    }
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

onMounted(fetchData)
</script>

<style scoped lang="scss">
.flow-config {
  padding: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
