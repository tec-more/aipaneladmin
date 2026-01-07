<template>
  <div class="customer-detail">
    <el-card shadow="never" class="detail-card">
      <template #header>
        <div class="card-header">
          <el-button type="primary" :icon="Back" @click="handleBack">返回列表</el-button>
          <span class="detail-title">客户详情</span>
        </div>
      </template>

      <div class="loading-container" v-if="loading">
        <el-skeleton :rows="10" animated />
      </div>

      <div v-else class="detail-content">
        <el-row :gutter="24">
          <el-col :span="24" class="detail-info">
            <h2 class="customer-name">{{ customer?.name }}</h2>
            <el-divider />
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">客户ID:</span>
                  <span class="info-value">{{ customer?.id }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">邮箱:</span>
                  <span class="info-value">{{ customer?.email }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">手机:</span>
                  <span class="info-value">{{ customer?.phone }}</span>
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">积分:</span>
                  <span class="info-value points">{{ customer?.points }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">会员状态:</span>
                  <el-tag v-if="customer?.is_vip" type="success">
                    是
                  </el-tag>
                  <el-tag v-else type="info">
                    否
                  </el-tag>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">会员到期:</span>
                  <span class="info-value">{{ customer?.vip_expire_at || '无' }}</span>
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">状态:</span>
                  <el-tag v-if="customer?.is_active" type="success">
                    启用
                  </el-tag>
                  <el-tag v-else type="danger">
                    禁用
                  </el-tag>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">注册时间:</span>
                  <span class="info-value">{{ customer?.created_at }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">更新时间:</span>
                  <span class="info-value">{{ customer?.updated_at }}</span>
                </div>
              </el-col>
            </el-row>

            <el-divider />
            <div class="detail-section">
              <h3 class="section-title">客户信息</h3>
              <div class="info-item">
                <span class="info-label">地址:</span>
                <span class="info-value">{{ customer?.address || '无' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">备注:</span>
                <span class="info-value">{{ customer?.remark || '无' }}</span>
              </div>
            </div>

            <div class="detail-actions">
              <el-button type="primary" :icon="Edit" @click="handleEdit">编辑</el-button>
              <el-button v-if="customer?.is_active" type="warning" :icon="SwitchButton" @click="handleToggleStatus">禁用</el-button>
              <el-button v-else type="success" :icon="SwitchButton" @click="handleToggleStatus">启用</el-button>
              <el-button type="danger" :icon="Delete" @click="handleDelete">删除</el-button>
            </div>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Back, Edit, Delete, SwitchButton } from '@element-plus/icons-vue'
import { getCustomerDetail, toggleCustomerStatus, deleteCustomer } from '@/api/customer'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const customer = ref(null)

const customerId = computed(() => route.params.id)

const fetchCustomerDetail = async () => {
  if (!customerId.value) return

  loading.value = true
  try {
    const res = await getCustomerDetail(customerId.value)
    customer.value = res.data
  } catch (e) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

const handleBack = () => {
  router.push('/customer')
}

const handleEdit = () => {
  router.push(`/customer/edit/${customerId.value}`)
}

const handleToggleStatus = async () => {
  try {
    await toggleCustomerStatus(customerId.value)
    ElMessage.success(customer.value.is_active ? '已禁用' : '已启用')
    fetchCustomerDetail()
  } catch (e) {
    // 错误已处理
  }
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除客户 "${customer.value?.name}" 吗？`, '提示', {
      type: 'warning'
    })
    await deleteCustomer(customerId.value)
    ElMessage.success('删除成功')
    router.push('/customer')
  } catch (e) {
    // 取消或错误
  }
}

onMounted(() => {
  fetchCustomerDetail()
})
</script>

<style lang="scss" scoped>
.customer-detail {
  .detail-card {
    .card-header {
      display: flex;
      align-items: center;
      gap: 16px;

      .detail-title {
        font-size: 18px;
        font-weight: bold;
      }
    }
  }

  .loading-container {
    padding: 20px 0;
  }

  .detail-content {
    .detail-info {
      .customer-name {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 20px;
      }

      .info-item {
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;

        .info-label {
          font-weight: bold;
          color: #606266;
          min-width: 80px;
        }

        .info-value {
          color: #303133;

          &.points {
            font-size: 18px;
            font-weight: bold;
            color: #e6a23c;
          }
        }

        .tag-item {
          margin-right: 8px;
        }

        .no-tags {
          color: #909399;
        }
      }
    }

    .detail-section {
      margin-top: 30px;

      .section-title {
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 16px;
        color: #303133;
      }

      .description {
        color: #606266;
        line-height: 1.8;
      }
    }

    .detail-actions {
      margin-top: 40px;
      display: flex;
      gap: 12px;
    }
  }
}
</style>