<template>
  <div class="rule-config">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>审批规则配置</span>
          <el-button type="primary" @click="handleCreate">新建规则</el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        class="tip-alert"
        title="审批规则用于拦截业务操作。配置了规则后，对应的业务接口（如创建采购订单）将自动被拦截并要求先提交审批。"
      />

      <el-table v-loading="loading" :data="tableData" border stripe class="table-margin">
        <el-table-column prop="business_type" label="业务类型" width="140" />
        <el-table-column prop="model" label="业务模型" width="160" show-overflow-tooltip />
        <el-table-column prop="methods" label="拦截方法" width="160">
          <template #default="{ row }">
            <el-tag v-for="m in row.methods" :key="m" size="small" class="method-tag">{{ m }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="flow_name" label="关联流程" width="150" />
        <el-table-column prop="priority" label="优先级" width="80" align="center" />
        <el-table-column prop="is_active" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="(val) => handleToggleStatus(row, val)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="formData" label-width="100px">
        <el-form-item label="业务类型">
          <el-input v-model="formData.business_type" placeholder="如：purchase_order" />
        </el-form-item>
        <el-form-item label="业务模型">
          <el-select v-model="formData.model" placeholder="选择或输入业务模型" filterable allow-create default-first-option style="width: 100%">
            <el-option v-for="m in MODEL_OPTIONS" :key="m" :label="m" :value="m" />
          </el-select>
          <div class="form-tip">由框架从 Pydantic Model 自动推导（驼峰转下划线），如 PurchaseOrderCreate → purchase_order</div>
        </el-form-item>
        <el-form-item label="拦截方法">
          <el-checkbox-group v-model="formData.methods">
            <el-checkbox value="POST" label="POST" />
            <el-checkbox value="PUT" label="PUT" />
            <el-checkbox value="DELETE" label="DELETE" />
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="关联流程">
          <el-select v-model="formData.flow_id" placeholder="选择审批流程" filterable style="width: 100%">
            <el-option v-for="f in flowOptions" :key="f.id" :label="f.name" :value="f.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="formData.priority" :min="0" :max="999" />
          <div class="form-tip">数字越大优先级越高</div>
        </el-form-item>
        <el-form-item label="规则说明">
          <el-input v-model="formData.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
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
import { getRuleList, createRule, updateRule, deleteRule, toggleRuleStatus, getFlowList } from '@/api/approval'

const loading = ref(false)
const tableData = ref([])
const flowOptions = ref([])
const MODEL_OPTIONS = ['purchase_order', 'purchase_receipt', 'sales_order', 'inventory_adjust']
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogMode = ref('create')

const pagination = reactive({ page: 1, page_size: 10, total: 0 })
const formData = reactive({
  id: null,
  business_type: '',
  model: '',
  methods: ['POST'],
  flow_id: null,
  priority: 0,
  description: '',
  is_active: true
})

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getRuleList(pagination)
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

const fetchFlows = async () => {
  try {
    const res = await getFlowList({ page: 1, page_size: 100 })
    if (res.code === 0 || res.code === 200 || res.success) {
      flowOptions.value = res.data.items || []
    }
  } catch (e) {
    console.error(e)
  }
}

const resetForm = () => {
  Object.assign(formData, {
    id: null, business_type: '', model: '', methods: ['POST'],
    flow_id: null, priority: 0, description: '', is_active: true
  })
}

const handleCreate = () => {
  resetForm()
  dialogMode.value = 'create'
  dialogTitle.value = '新建规则'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  resetForm()
  Object.assign(formData, {
    id: row.id, business_type: row.business_type, model: row.model || '',
    methods: row.methods || ['POST'], flow_id: row.flow_id, priority: row.priority,
    description: row.description || '', is_active: row.is_active
  })
  dialogMode.value = 'edit'
  dialogTitle.value = '编辑规则'
  dialogVisible.value = true
}

const handleToggleStatus = async (row, val) => {
  try {
    await toggleRuleStatus(row.id, val)
    ElMessage.success('状态已更新')
  } catch (e) {
    row.is_active = !val
    console.error(e)
  }
}

const submitForm = async () => {
  try {
    if (dialogMode.value === 'create') {
      const { id, ...data } = formData
      const res = await createRule(data)
      if (res.code === 0 || res.code === 200 || res.success) {
        ElMessage.success('创建成功')
      }
    } else {
      const { id, ...data } = formData
      const res = await updateRule(id, data)
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
    await ElMessageBox.confirm(`确定删除规则「${row.business_type}」吗？`, '提示', { type: 'warning' })
    const res = await deleteRule(row.id)
    if (res.code === 0 || res.code === 200 || res.success) {
      ElMessage.success('删除成功')
      fetchData()
    }
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

onMounted(() => {
  fetchData()
  fetchFlows()
})
</script>

<style scoped lang="scss">
.rule-config {
  padding: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tip-alert {
  margin-bottom: 16px;
}

.table-margin {
  margin-top: 8px;
}

.method-tag {
  margin-right: 4px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  margin-top: 4px;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
