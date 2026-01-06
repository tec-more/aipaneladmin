<template>
  <div class="order-management">
    <!-- 搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="订单号">
          <el-input v-model="searchForm.order_no" placeholder="请输入订单号" clearable />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="searchForm.customer_name" placeholder="请输入客户名称" clearable />
        </el-form-item>
        <el-form-item label="产品名称">
          <el-input v-model="searchForm.product_name" placeholder="请输入产品名称" clearable />
        </el-form-item>
        <el-form-item label="订单状态">
          <el-select v-model="searchForm.status" placeholder="请选择" clearable style="width: 120px">
            <el-option label="待处理" :value="'pending'" />
            <el-option label="已完成" :value="'completed'" />
            <el-option label="已取消" :value="'cancelled'" />
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
          <span>订单列表</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增订单</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="order_no" label="订单号" min-width="150" />
        <el-table-column prop="customer_name" label="客户名称" min-width="120" />
        <el-table-column prop="product_name" label="产品名称" min-width="120" />
        <el-table-column prop="price" label="价格" width="100" align="center">
          <template #default="{ row }">
            ¥{{ row.price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column label="订单状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'pending'" type="warning">
              待处理
            </el-tag>
            <el-tag v-else-if="row.status === 'completed'" type="success">
              已完成
            </el-tag>
            <el-tag v-else-if="row.status === 'cancelled'" type="danger">
              已取消
            </el-tag>
            <el-tag v-else type="info">
              其他
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link :icon="Edit" @click="handleEdit(row)">编辑</el-button>
            <el-button v-if="row.status === 'pending'" type="success" link :icon="Check" @click="handleComplete(row)">完成</el-button>
            <el-button v-if="row.status === 'pending'" type="warning" link :icon="Close" @click="handleCancel(row)">取消</el-button>
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
      :title="isEdit ? '编辑订单' : '新增订单'"
      width="600px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="订单号" prop="order_no">
          <el-input v-model="form.order_no" placeholder="请输入订单号" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="客户" prop="customer_id">
          <el-select v-model="form.customer_id" placeholder="请选择客户">
            <el-option
              v-for="customer in customerOptions"
              :key="customer.id"
              :label="customer.name"
              :value="customer.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="产品" prop="product_id">
          <el-select v-model="form.product_id" placeholder="请选择产品">
            <el-option
              v-for="product in productOptions"
              :key="product.id"
              :label="product.name"
              :value="product.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input-number v-model="form.price" :min="0.01" :step="0.01" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="订单状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择订单状态">
            <el-option label="待处理" :value="'pending'" />
            <el-option label="已完成" :value="'completed'" />
            <el-option label="已取消" :value="'cancelled'" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Edit, Delete, Check, Close } from '@element-plus/icons-vue'
import {
  getOrderList,
  createOrder,
  updateOrder,
  deleteOrder,
  completeOrder,
  cancelOrder
} from '@/api/order'
import {
  getCustomerList
} from '@/api/customer'
import {
  getProductList
} from '@/api/product'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const tableData = ref([])
const customerOptions = ref([])
const productOptions = ref([])

const searchForm = reactive({
  order_no: '',
  customer_name: '',
  product_name: '',
  status: null
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const form = ref({
  order_no: '',
  customer_id: '',
  product_id: '',
  price: 0,
  status: 'pending'
})

const rules = {
  order_no: [
    { required: true, message: '请输入订单号', trigger: 'blur' },
    { min: 6, max: 30, message: '订单号长度在6-30个字符', trigger: 'blur' }
  ],
  customer_id: [
    { required: true, message: '请选择客户', trigger: 'change' }
  ],
  product_id: [
    { required: true, message: '请选择产品', trigger: 'change' }
  ],
  price: [
    { required: true, message: '请输入价格', trigger: 'blur' },
    { type: 'number', min: 0.01, message: '价格不能少于0.01', trigger: 'blur' }
  ],
  status: [
    { required: true, message: '请选择订单状态', trigger: 'change' }
  ]
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getOrderList({
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

const fetchCustomers = async () => {
  try {
    const res = await getCustomerList({
      page: 1,
      page_size: 1000
    })
    customerOptions.value = res.data.items
  } catch (e) {
    // 错误已处理
  }
}

const fetchProducts = async () => {
  try {
    const res = await getProductList({
      page: 1,
      page_size: 1000
    })
    productOptions.value = res.data.items
  } catch (e) {
    // 错误已处理
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  searchForm.order_no = ''
  searchForm.customer_name = ''
  searchForm.product_name = ''
  searchForm.status = null
  handleSearch()
}

const handleAdd = async () => {
  isEdit.value = false
  form.value = {
    order_no: generateOrderNo(),
    customer_id: '',
    product_id: '',
    price: 0,
    status: 'pending'
  }
  await fetchCustomers()
  await fetchProducts()
  dialogVisible.value = true
}

const handleEdit = async (row) => {
  isEdit.value = true
  form.value = {
    id: row.id,
    order_no: row.order_no,
    customer_id: row.customer_id,
    product_id: row.product_id,
    price: row.price,
    status: row.status
  }
  await fetchCustomers()
  await fetchProducts()
  dialogVisible.value = true
}

const handleSubmit = async () => {
  await formRef.value.validate()

  submitLoading.value = true
  try {
    if (isEdit.value) {
      await updateOrder(form.value.id, {
        customer_id: form.value.customer_id,
        product_id: form.value.product_id,
        price: form.value.price,
        status: form.value.status
      })
      ElMessage.success('更新成功')
    } else {
      await createOrder(form.value)
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

const handleComplete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要完成订单 "${row.order_no}" 吗？`, '提示', {
      type: 'success'
    })
    await completeOrder(row.id)
    ElMessage.success('订单已完成')
    fetchData()
  } catch (e) {
    // 取消或错误
  }
}

const handleCancel = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要取消订单 "${row.order_no}" 吗？`, '提示', {
      type: 'warning'
    })
    await cancelOrder(row.id)
    ElMessage.success('订单已取消')
    fetchData()
  } catch (e) {
    // 取消或错误
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除订单 "${row.order_no}" 吗？`, '提示', {
      type: 'warning'
    })
    await deleteOrder(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (e) {
    // 取消或错误
  }
}

const resetForm = () => {
  formRef.value?.resetFields()
}

const generateOrderNo = () => {
  const date = new Date()
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')
  const random = String(Math.floor(Math.random() * 1000)).padStart(3, '0')
  return `ORD${year}${month}${day}${hour}${minute}${second}${random}`
}

onMounted(() => {
  fetchData()
})
</script>

<style lang="scss" scoped>
.order-management {
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
}
</style>