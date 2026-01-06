<template>
  <div class="product-management">
    <!-- 搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="产品名称">
          <el-input v-model="searchForm.name" placeholder="请输入产品名称" clearable />
        </el-form-item>
        <el-form-item label="产品类型">
          <el-select v-model="searchForm.product_type" placeholder="请选择" clearable style="width: 120px">
            <el-option label="点卷" :value="'points'" />
            <el-option label="会员" :value="'membership'" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.is_active" placeholder="请选择" clearable style="width: 120px">
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span>产品列表</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增产品</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="name" label="产品名称" min-width="120" />
        <el-table-column label="产品类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.product_type === 'points'" type="success">
              点卷
            </el-tag>
            <el-tag v-else-if="row.product_type === 'membership'" type="warning">
              会员
            </el-tag>
            <el-tag v-else type="info">
              其他
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="100" align="center">
          <template #default="{ row }">
            ¥{{ row.price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="value" label="产品价值" width="100" align="center" />
        <el-table-column prop="stock" label="库存" width="100" align="center" />
        <el-table-column prop="sales_count" label="销售数量" width="100" align="center" />
        <el-table-column prop="description" label="产品描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="handleToggleStatus(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link :icon="Edit" @click="handleEdit(row)">编辑</el-button>
            <el-button type="success" link :icon="Box" @click="handleUpdateStock(row)">库存</el-button>
            <el-button type="danger" link :icon="Delete" @click="handleDelete(row)">
              删除
            </el-button>
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
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑产品' : '新增产品'"
      width="600px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="产品名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入产品名称" />
        </el-form-item>
        <el-form-item label="产品类型" prop="product_type">
          <el-radio-group v-model="form.product_type">
            <el-radio label="points">点卷</el-radio>
            <el-radio label="membership">会员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input-number v-model="form.price" :min="0.01" :step="0.01" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="产品价值" prop="value">
          <el-input-number v-model="form.value" :min="1" :step="1" style="width: 100%" />
          <div class="form-tip">
            <span v-if="form.product_type === 'points'">点卷数量</span>
            <span v-else-if="form.product_type === 'membership'">会员天数</span>
          </div>
        </el-form-item>
        <el-form-item label="库存" prop="stock">
          <el-input-number v-model="form.stock" :min="0" :step="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="产品描述">
          <el-input v-model="form.description" type="textarea" placeholder="请输入产品描述" rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 库存管理弹窗 -->
    <el-dialog v-model="stockDialogVisible" title="库存管理" width="400px">
      <div class="stock-dialog-content">
        <p class="stock-tip">当前产品: <strong>{{ currentProduct?.name }}</strong></p>
        <p class="stock-tip">当前库存: <strong>{{ currentProduct?.stock }}</strong></p>
        <el-form ref="stockFormRef" :model="stockForm" :rules="stockRules" label-width="80px">
          <el-form-item label="调整数量" prop="stock">
            <el-input-number v-model="stockForm.stock" :step="10" style="width: 100%" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="stockDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="stockLoading" @click="handleStockSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Edit, Delete, Box } from '@element-plus/icons-vue'
import {
  getProductList,
  createProduct,
  updateProduct,
  deleteProduct,
  toggleProductStatus,
  updateProductStock
} from '@/api/product'

const loading = ref(false)
const submitLoading = ref(false)
const stockLoading = ref(false)
const dialogVisible = ref(false)
const stockDialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const stockFormRef = ref(null)

const tableData = ref([])
const currentProduct = ref(null)

const searchForm = reactive({
  name: '',
  product_type: null,
  is_active: null
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const form = ref({
  name: '',
  product_type: 'points',
  price: 0,
  value: 100,
  stock: 1000,
  description: ''
})

const stockForm = reactive({
  stock: 0
})

const rules = {
  name: [
    { required: true, message: '请输入产品名称', trigger: 'blur' },
    { min: 2, max: 50, message: '产品名称长度在2-50个字符', trigger: 'blur' }
  ],
  product_type: [
    { required: true, message: '请选择产品类型', trigger: 'change' }
  ],
  price: [
    { required: true, message: '请输入价格', trigger: 'blur' },
    { type: 'number', min: 0.01, message: '价格不能少于0.01', trigger: 'blur' }
  ],
  value: [
    { required: true, message: '请输入产品价值', trigger: 'blur' },
    { type: 'number', min: 1, message: '产品价值不能少于1', trigger: 'blur' }
  ]
}

const stockRules = {
  stock: [
    { required: true, message: '请输入调整数量', trigger: 'blur' },
    { type: 'number', message: '请输入有效数字', trigger: 'blur' }
  ]
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getProductList({
      page: pagination.page,
      page_size: pagination.pageSize,
      ...searchForm
    })
    tableData.value = res.data.items
    pagination.total = res.data.total
  } catch (e) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  searchForm.name = ''
  searchForm.product_type = null
  searchForm.is_active = null
  handleSearch()
}

const handleAdd = () => {
  isEdit.value = false
  form.value = {
    name: '',
    product_type: 'points',
    price: 0,
    value: 100,
    stock: 1000,
    description: ''
  }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  form.value = {
    id: row.id,
    name: row.name,
    product_type: row.product_type,
    price: row.price,
    value: row.value,
    stock: row.stock,
    description: row.description || ''
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  await formRef.value.validate()

  submitLoading.value = true
  try {
    if (isEdit.value) {
      await updateProduct(form.value.id, {
        name: form.value.name,
        product_type: form.value.product_type,
        price: form.value.price,
        value: form.value.value,
        stock: form.value.stock,
        description: form.value.description
      })
      ElMessage.success('更新成功')
    } else {
      await createProduct(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    // 错误已处理
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除产品 "${row.name}" 吗？`, '提示', {
      type: 'warning'
    })
    await deleteProduct(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (e) {
    // 取消或错误
  }
}

const handleToggleStatus = async (row) => {
  try {
    await toggleProductStatus(row.id)
    ElMessage.success(row.is_active ? '已启用' : '已禁用')
  } catch (e) {
    row.is_active = !row.is_active
  }
}

const handleUpdateStock = (row) => {
  currentProduct.value = row
  stockForm.stock = 0
  stockDialogVisible.value = true
}

const handleStockSubmit = async () => {
  await stockFormRef.value.validate()

  stockLoading.value = true
  try {
    await updateProductStock(currentProduct.value.id, {
      stock: stockForm.stock
    })
    ElMessage.success('库存调整成功')
    stockDialogVisible.value = false
    fetchData()
  } catch (e) {
    // 错误已处理
  } finally {
    stockLoading.value = false
  }
}

const resetForm = () => {
  formRef.value?.resetFields()
  stockFormRef.value?.resetFields()
}

onMounted(() => {
  fetchData()
})
</script>

<style lang="scss" scoped>
.product-management {
  .search-card {
    margin-bottom: 16px;

    .search-form {
      display: flex;
      flex-wrap: wrap;

      .el-form-item {
        margin-bottom: 0;
        margin-right: 16px;
      }
    }
  }

  .table-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  .pagination-wrapper {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
  }

  .form-tip {
    margin-top: 8px;
    font-size: 12px;
    color: #999;
  }

  .stock-dialog-content {
    .stock-tip {
      margin-bottom: 16px;
      color: #666;
    }
  }
}
</style>