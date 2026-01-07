<template>
  <div class="order-detail">
    <el-card shadow="never" class="detail-card">
      <template #header>
        <div class="card-header">
          <el-button type="primary" :icon="Back" @click="handleBack">返回列表</el-button>
          <span class="detail-title">订单详情</span>
        </div>
      </template>

      <div class="detail-content">
        <div class="info-section">
          <div class="info-item">
            <label class="info-label">订单ID：</label>
            <span class="info-value">{{ orderInfo.id }}</span>
          </div>
          <div class="info-item">
            <label class="info-label">订单号：</label>
            <span class="info-value">{{ orderInfo.order_no }}</span>
          </div>
          <div class="info-item">
            <label class="info-label">客户名称：</label>
            <span class="info-value">{{ orderInfo.customer_name }}</span>
          </div>
          <div class="info-item">
            <label class="info-label">产品名称：</label>
            <span class="info-value">{{ orderInfo.product_name }}</span>
          </div>
          <div class="info-item">
            <label class="info-label">价格：</label>
            <span class="info-value">¥{{ orderInfo.price ? orderInfo.price.toFixed(2) : '0.00' }}</span>
          </div>
          <div class="info-item">
            <label class="info-label">订单状态：</label>
            <span class="info-value">
              <el-tag v-if="orderInfo.status === 'pending'" type="warning">待处理</el-tag>
              <el-tag v-else-if="orderInfo.status === 'completed'" type="success">已完成</el-tag>
              <el-tag v-else-if="orderInfo.status === 'cancelled'" type="danger">已取消</el-tag>
              <el-tag v-else type="info">其他</el-tag>
            </span>
          </div>
          <div class="info-item">
            <label class="info-label">创建时间：</label>
            <span class="info-value">{{ orderInfo.created_at }}</span>
          </div>
        </div>

        <div class="action-section">
          <el-button type="primary" :icon="Edit" @click="handleEdit">编辑</el-button>
          <el-button v-if="orderInfo.status === 'pending'" type="success" :icon="Check" @click="handleComplete">完成</el-button>
          <el-button v-if="orderInfo.status === 'pending'" type="warning" :icon="Close" @click="handleCancel">取消</el-button>
          <el-button type="danger" :icon="Delete" @click="handleDelete">删除</el-button>
        </div>
      </div>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="'编辑订单'"
      width="600px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="订单号" prop="order_no">
          <el-input v-model="form.order_no" placeholder="请输入订单号" disabled />
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
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Back, Edit, Delete, Check, Close } from '@element-plus/icons-vue'
import {
  getOrderDetail,
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

const route = useRoute()
const router = useRouter()
const orderInfo = ref({})
const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const formRef = ref(null)

const customerOptions = ref([])
const productOptions = ref([])

const form = ref({
  id: '',
  order_no: '',
  customer_id: '',
  product_id: '',
  price: 0,
  status: 'pending'
})

const rules = {
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

const fetchOrderDetail = async () => {
  loading.value = true
  try {
    const res = await getOrderDetail(route.params.id)
    orderInfo.value = res.data
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

const handleBack = () => {
  router.push('/order')
}

const handleEdit = async () => {
  form.value = {
    id: orderInfo.value.id,
    order_no: orderInfo.value.order_no,
    customer_id: orderInfo.value.customer_id,
    product_id: orderInfo.value.product_id,
    price: orderInfo.value.price,
    status: orderInfo.value.status
  }
  await fetchCustomers()
  await fetchProducts()
  dialogVisible.value = true
}

const handleSubmit = async () => {
  await formRef.value.validate()

  submitLoading.value = true
  try {
    await updateOrder(form.value.id, {
      customer_id: form.value.customer_id,
      product_id: form.value.product_id,
      price: form.value.price,
      status: form.value.status
    })
    ElMessage.success('更新成功')
    dialogVisible.value = false
    fetchOrderDetail()
  } catch (e) {
    // 错误已处理
  } finally {
    submitLoading.value = false
  }
}

const handleComplete = async () => {
  try {
    await ElMessageBox.confirm(`确定要完成订单 "${orderInfo.value.order_no}" 吗？`, '提示', {
      type: 'success'
    })
    await completeOrder(orderInfo.value.id)
    ElMessage.success('订单已完成')
    fetchOrderDetail()
  } catch (e) {
    // 取消或错误
  }
}

const handleCancel = async () => {
  try {
    await ElMessageBox.confirm(`确定要取消订单 "${orderInfo.value.order_no}" 吗？`, '提示', {
      type: 'warning'
    })
    await cancelOrder(orderInfo.value.id)
    ElMessage.success('订单已取消')
    fetchOrderDetail()
  } catch (e) {
    // 取消或错误
  }
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除订单 "${orderInfo.value.order_no}" 吗？`, '提示', {
      type: 'warning'
    })
    await deleteOrder(orderInfo.value.id)
    ElMessage.success('删除成功')
    router.push('/order')
  } catch (e) {
    // 取消或错误
  }
}

const resetForm = () => {
  formRef.value?.resetFields()
}

onMounted(() => {
  fetchOrderDetail()
})
</script>

<style lang="scss" scoped>
.order-detail {
  .detail-card {
    .card-header {
      display: flex;
      align-items: center;

      .detail-title {
        margin-left: 16px;
        font-size: 18px;
        font-weight: bold;
      }
    }
  }

  .detail-content {
    padding: 20px 0;

    .info-section {
      display: flex;
      flex-wrap: wrap;
      gap: 20px 40px;
      margin-bottom: 32px;

      .info-item {
        display: flex;
        align-items: center;

        .info-label {
          min-width: 100px;
          font-weight: bold;
          color: #606266;
        }

        .info-value {
          color: #303133;
        }
      }
    }

    .action-section {
      display: flex;
      gap: 12px;
      border-top: 1px solid #ebeef5;
      padding-top: 20px;
    }
  }
}
</style>