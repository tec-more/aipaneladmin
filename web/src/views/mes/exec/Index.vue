<template>
  <div class="mes-exec">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="生产订单号">
          <el-input v-model="searchForm.order_code" placeholder="请输入订单号" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择" clearable style="width: 120px">
            <el-option label="待生产" value="pending" />
            <el-option label="生产中" value="producing" />
            <el-option label="已完成" value="completed" />
            <el-option label="已暂停" value="paused" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span>生产订单列表</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增订单</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="order_code" label="生产订单号" min-width="140" />
        <el-table-column prop="product_name" label="产品名称" min-width="150" />
        <el-table-column prop="quantity" label="生产数量" width="100" align="center" />
        <el-table-column prop="completed_quantity" label="已完成数量" width="120" align="center" />
        <el-table-column label="完成进度" width="180" align="center">
          <template #default="{ row }">
            <el-progress :percentage="row.quantity ? Math.round((row.completed_quantity || 0) / row.quantity * 100) : 0" :stroke-width="12" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTypeMap[row.status] || 'info'">
              {{ statusMap[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link :icon="Edit" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

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

    <!-- 新增/编辑生产订单对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      :close-on-click-modal="false"
      @close="handleDialogClose"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="120px">
        <el-form-item label="订单编号" prop="order_code">
          <el-input v-model="formData.order_code" placeholder="请输入订单编号" />
        </el-form-item>
        <el-form-item label="产品名称" prop="product_name">
          <el-input v-model="formData.product_name" placeholder="请输入产品名称" />
        </el-form-item>
        <el-form-item label="生产数量" prop="quantity">
          <el-input-number v-model="formData.quantity" :min="1" :max="999999" placeholder="请输入生产数量" style="width: 100%" />
        </el-form-item>
        <el-form-item label="计划开始日期" prop="plan_start_date">
          <el-date-picker
            v-model="formData.plan_start_date"
            type="date"
            placeholder="请选择计划开始日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="计划结束日期" prop="plan_end_date">
          <el-date-picker
            v-model="formData.plan_end_date"
            type="date"
            placeholder="请选择计划结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="formData.priority" placeholder="请选择优先级" style="width: 100%">
            <el-option label="低" :value="1" />
            <el-option label="中" :value="2" />
            <el-option label="高" :value="3" />
            <el-option label="紧急" :value="4" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="formData.remark" type="textarea" :rows="3" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saveLoading" @click="handleSave">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { getProductionOrderList, createProductionOrder, updateProductionOrder, deleteProductionOrder } from '@/api/mes'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('新增生产订单')
const saveLoading = ref(false)
const formRef = ref(null)
const isEdit = ref(false)
const editId = ref(null)

const searchForm = reactive({
  order_code: '',
  status: null
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const formData = reactive({
  order_code: '',
  product_name: '',
  quantity: 1,
  plan_start_date: '',
  plan_end_date: '',
  priority: 2,
  remark: ''
})

const formRules = {
  order_code: [{ required: true, message: '请输入订单编号', trigger: 'blur' }],
  product_name: [{ required: true, message: '请输入产品名称', trigger: 'blur' }],
  quantity: [{ required: true, message: '请输入生产数量', trigger: 'blur' }]
}

const statusMap = {
  pending: '待生产',
  producing: '生产中',
  completed: '已完成',
  paused: '已暂停'
}

const statusTypeMap = {
  pending: 'info',
  producing: 'warning',
  completed: 'success',
  paused: 'danger'
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getProductionOrderList({
      page: pagination.page,
      page_size: pagination.pageSize,
      ...searchForm
    })
    tableData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (e) { console.error('获取生产订单失败:', e) }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.page = 1; fetchData() }
const handleReset = () => { searchForm.order_code = ''; searchForm.status = null; handleSearch() }

const handleAdd = () => {
  isEdit.value = false
  editId.value = null
  dialogTitle.value = '新增生产订单'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  editId.value = row.id
  dialogTitle.value = '编辑生产订单'
  formData.order_code = row.order_code || ''
  formData.product_name = row.product_name || ''
  formData.quantity = row.quantity || 1
  formData.plan_start_date = row.plan_start_date || ''
  formData.plan_end_date = row.plan_end_date || ''
  formData.priority = row.priority || 2
  formData.remark = row.remark || ''
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定要删除订单 "${row.order_code}" 吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteProductionOrder(row.id)
      ElMessage.success('删除成功')
      fetchData()
    } catch (e) {
      console.error('删除失败:', e)
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const handleSave = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      saveLoading.value = true
      try {
        if (isEdit.value) {
          await updateProductionOrder(editId.value, formData)
          ElMessage.success('更新成功')
        } else {
          await createProductionOrder(formData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchData()
      } catch (e) {
        console.error('保存失败:', e)
        ElMessage.error('保存失败')
      } finally {
        saveLoading.value = false
      }
    }
  })
}

const resetForm = () => {
  formData.order_code = ''
  formData.product_name = ''
  formData.quantity = 1
  formData.plan_start_date = ''
  formData.plan_end_date = ''
  formData.priority = 2
  formData.remark = ''
  formRef.value?.clearValidate()
}

const handleDialogClose = () => {
  resetForm()
}

onMounted(() => { fetchData() })
</script>

<style lang="scss" scoped>
.mes-exec {
  .search-card { margin-bottom: 16px;
    .search-form { display: flex; flex-wrap: wrap;
      .el-form-item { margin-bottom: 0; margin-right: 16px; }
    }
  }
  .table-card {
    .card-header { display: flex; justify-content: space-between; align-items: center; }
  }
  .pagination-wrapper { margin-top: 16px; display: flex; justify-content: flex-end; }
}
</style>
