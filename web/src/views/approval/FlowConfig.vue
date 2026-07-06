<template>
  <div class="flow-config">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>审批流程配置</span>
          <el-button type="primary" @click="openDialog('create')">新建流程</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="name" label="流程名称" min-width="150" />
        <el-table-column prop="code" label="流程编码" width="160" />
        <el-table-column prop="business_type" label="业务类型" width="130">
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
            <el-button type="primary" link @click="openDialog('edit', row)">编辑</el-button>
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

    <!-- 设计器对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="1280px"
      top="4vh"
      destroy-on-close
      class="flow-designer-dialog"
    >
      <el-form :model="formData" label-width="96px" ref="formRef">
        <div class="base-grid">
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
            <el-input v-model="formData.business_type" placeholder="如：purchase_order, expense" />
          </el-form-item>
          <el-form-item label="是否启用">
            <el-switch v-model="formData.is_active" />
          </el-form-item>
        </div>
        <el-form-item label="流程描述">
          <el-input v-model="formData.description" type="textarea" :rows="2" />
        </el-form-item>

        <el-divider>流程节点设计（拖拽连线，右侧配置审批方式）</el-divider>
        <ApprovalFlowCanvas ref="canvasRef" />
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存流程</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getFlowList, createFlow, updateFlow, deleteFlow, toggleFlowStatus, validateFlow
} from '@/api/approval'
import ApprovalFlowCanvas from '@/components/approval/ApprovalFlowCanvas.vue'

const loading = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogMode = ref('create')
const canvasRef = ref()

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
}

const openDialog = (mode, row) => {
  resetForm()
  dialogMode.value = mode
  dialogTitle.value = mode === 'create' ? '新建流程' : '编辑流程'
  if (row) {
    Object.assign(formData, {
      id: row.id, name: row.name, code: row.code, business_type: row.business_type || '',
      description: row.description || '', is_active: row.is_active,
      form_config: row.form_config || [], flow_config: row.flow_config || {}
    })
  }
  dialogVisible.value = true
  nextTick(() => {
    canvasRef.value?.load(mode === 'edit' ? (row?.flow_config || {}) : null)
  })
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
  let flowConfig = {}
  try {
    flowConfig = canvasRef.value?.serialize() || {}
  } catch (e) {
    ElMessage.error('读取流程设计失败')
    return
  }
  if (!flowConfig.nodes || !flowConfig.nodes.length) {
    ElMessage.error('请至少添加一个流程节点')
    return
  }
  formData.flow_config = flowConfig

  // 前端预校验
  try {
    const vres = await validateFlow({ ...formData })
    const data = vres?.data || vres
    if (data && data.valid === false) {
      ElMessage.error('流程配置有误：' + (data.errors || []).join('；'))
      return
    }
  } catch (e) {
    // 校验接口异常不阻断保存，交由 create/update 兜底
  }

  try {
    let res
    if (dialogMode.value === 'create') {
      res = await createFlow({ ...formData })
    } else {
      const { id, ...updateData } = formData
      res = await updateFlow(id, updateData)
    }
    if (res.code === 0 || res.code === 200 || res.success) {
      ElMessage.success('保存成功')
      dialogVisible.value = false
      fetchData()
    } else {
      ElMessage.error(res.msg || '保存失败')
    }
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
.flow-config { padding: 16px; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.base-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 24px;
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

:deep(.flow-designer-dialog) {
  .el-dialog__body { padding-top: 12px; }
}
</style>
