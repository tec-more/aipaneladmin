<template>
  <div class="mes-plan">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="计划编号">
          <el-input v-model="searchForm.plan_code" placeholder="请输入计划编号" clearable />
        </el-form-item>
        <el-form-item label="产品名称">
          <el-input v-model="searchForm.product_name" placeholder="请输入产品名称" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择" clearable style="width: 120px">
            <el-option label="草稿" value="draft" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
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
          <span>生产计划列表</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新建计划</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="plan_code" label="计划编号" min-width="140" />
        <el-table-column prop="product_name" label="产品名称" min-width="150" />
        <el-table-column prop="planned_quantity" label="计划数量" width="100" align="center" />
        <el-table-column prop="start_date" label="开始日期" width="120" align="center" />
        <el-table-column prop="end_date" label="结束日期" width="120" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTypeMap[row.status] || 'info'">
              {{ statusMap[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
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

    <!-- 新增/编辑生产计划对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="计划编号" prop="plan_code">
          <el-input v-model="formData.plan_code" placeholder="请输入计划编号" />
        </el-form-item>
        <el-form-item label="产品名称" prop="product_name">
          <el-input v-model="formData.product_name" placeholder="请输入产品名称" />
        </el-form-item>
        <el-form-item label="计划数量" prop="planned_quantity">
          <el-input-number v-model="formData.planned_quantity" :min="1" placeholder="请输入计划数量" style="width: 100%" />
        </el-form-item>
        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker
            v-model="formData.start_date"
            type="date"
            placeholder="请选择开始日期"
            style="width: 100%"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="结束日期" prop="end_date">
          <el-date-picker
            v-model="formData.end_date"
            type="date"
            placeholder="请选择结束日期"
            style="width: 100%"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="formData.status" placeholder="请选择状态" style="width: 100%">
            <el-option label="草稿" value="draft" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
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
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import { getProductionPlanList, createProductionPlan } from '@/api/mes'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const tableData = ref([])

// 对话框相关
const dialogVisible = ref(false)
const dialogTitle = ref('新建生产计划')
const saveLoading = ref(false)
const formRef = ref(null)

// 表单数据
const formData = reactive({
  plan_code: '',
  product_name: '',
  planned_quantity: null,
  start_date: '',
  end_date: '',
  status: 'draft',
  remark: ''
})

// 表单验证规则
const formRules = {
  plan_code: [{ required: true, message: '请输入计划编号', trigger: 'blur' }],
  product_name: [{ required: true, message: '请输入产品名称', trigger: 'blur' }],
  planned_quantity: [{ required: true, message: '请输入计划数量', trigger: 'blur' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

const searchForm = reactive({
  plan_code: '',
  product_name: '',
  status: null
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const statusMap = {
  draft: '草稿',
  confirmed: '已确认',
  in_progress: '进行中',
  completed: '已完成',
  cancelled: '已取消'
}

const statusTypeMap = {
  draft: 'info',
  confirmed: 'warning',
  in_progress: 'primary',
  completed: 'success',
  cancelled: 'danger'
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getProductionPlanList({
      page: pagination.page,
      page_size: pagination.pageSize,
      ...searchForm
    })
    tableData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (e) { console.error('获取生产计划失败:', e) }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.page = 1; fetchData() }
const handleReset = () => { searchForm.plan_code = ''; searchForm.product_name = ''; searchForm.status = null; handleSearch() }

// 打开新建对话框
const handleAdd = () => {
  dialogTitle.value = '新建生产计划'
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  formData.plan_code = ''
  formData.product_name = ''
  formData.planned_quantity = null
  formData.start_date = ''
  formData.end_date = ''
  formData.status = 'draft'
  formData.remark = ''
}

// 对话框关闭回调
const handleDialogClose = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  resetForm()
}

// 保存生产计划
const handleSave = async () => {
  if (!formRef.value) return
  try {
    const valid = await formRef.value.validate()
    if (!valid) return
    saveLoading.value = true
    await createProductionPlan(formData)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    console.error('创建生产计划失败:', e)
    ElMessage.error(e.message || '创建失败')
  } finally {
    saveLoading.value = false
  }
}

onMounted(() => { fetchData() })
</script>

<style lang="scss" scoped>
.mes-plan {
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
