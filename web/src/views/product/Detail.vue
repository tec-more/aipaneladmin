<template>
  <div class="product-detail">
    <el-card shadow="never" class="detail-card">
      <template #header>
        <div class="card-header">
          <el-button type="primary" :icon="Back" @click="handleBack">返回列表</el-button>
          <span class="detail-title">产品详情</span>
        </div>
      </template>

      <div class="loading-container" v-if="loading">
        <el-skeleton :rows="10" animated />
      </div>

      <div v-else class="detail-content">
        <el-row :gutter="24">
          <el-col :span="24" class="detail-info">
            <h2 class="product-name">{{ product?.name }}</h2>
            <el-divider />
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">产品ID:</span>
                  <span class="info-value">{{ product?.id }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">产品类型:</span>
                  <el-tag v-if="product?.product_type === 'points'" type="success">
                    点卷
                  </el-tag>
                  <el-tag v-else-if="product?.product_type === 'membership'" type="warning">
                    会员
                  </el-tag>
                  <el-tag v-else type="info">
                    其他
                  </el-tag>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">价格:</span>
                  <span class="info-value price">¥{{ product?.price?.toFixed(2) }}</span>
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">产品价值:</span>
                  <span class="info-value">{{ product?.value }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">库存:</span>
                  <span class="info-value">{{ product?.stock }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">销售数量:</span>
                  <span class="info-value">{{ product?.sales_count }}</span>
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">浏览次数:</span>
                  <span class="info-value">{{ product?.view_count }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">状态:</span>
                  <el-tag v-if="product?.is_active" type="success">
                    启用
                  </el-tag>
                  <el-tag v-else type="danger">
                    禁用
                  </el-tag>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">热门产品:</span>
                  <el-tag v-if="product?.is_hot" type="warning">
                    是
                  </el-tag>
                  <el-tag v-else type="info">
                    否
                  </el-tag>
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">新品:</span>
                  <el-tag v-if="product?.is_new" type="primary">
                    是
                  </el-tag>
                  <el-tag v-else type="info">
                    否
                  </el-tag>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">创建时间:</span>
                  <span class="info-value">{{ product?.created_at }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="info-item">
                  <span class="info-label">更新时间:</span>
                  <span class="info-value">{{ product?.updated_at }}</span>
                </div>
              </el-col>
            </el-row>

            <el-divider />
            <div class="detail-section">
              <h3 class="section-title">产品描述</h3>
              <p class="description">{{ product?.description || '无描述' }}</p>
            </div>

            <div class="detail-section">
              <h3 class="section-title">分类与标签</h3>
              <div class="info-item">
                <span class="info-label">分类:</span>
                <span class="info-value">{{ product?.category || '无分类' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">标签:</span>
                <el-tag v-for="tag in product?.tags" :key="tag" type="info" size="small" class="tag-item">
                  {{ tag }}
                </el-tag>
                <span v-if="!product?.tags || product?.tags.length === 0" class="no-tags">无标签</span>
              </div>
            </div>

            <div class="detail-section" v-if="product?.images && product?.images.length > 0">
              <h3 class="section-title">产品图片</h3>
              <el-image
                v-for="(image, index) in product?.images"
                :key="index"
                :src="image"
                :preview-src-list="product?.images"
                class="product-image"
              />
            </div>

            <div class="detail-actions">
              <el-button type="primary" :icon="Edit" @click="handleEdit">编辑</el-button>
              <el-button v-if="product?.is_active" type="warning" :icon="SwitchButton" @click="handleToggleStatus">禁用</el-button>
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
import { getProductDetail, toggleProductStatus, deleteProduct } from '@/api/product'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const product = ref(null)

const productId = computed(() => route.params.id)

const fetchProductDetail = async () => {
  if (!productId.value) return

  loading.value = true
  try {
    const res = await getProductDetail(productId.value)
    product.value = res.data
  } catch (e) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

const handleBack = () => {
  router.push('/products')
}

const handleEdit = () => {
  router.push(`/products/edit/${productId.value}`)
}

const handleToggleStatus = async () => {
  try {
    await toggleProductStatus(productId.value)
    ElMessage.success(product.value.is_active ? '已禁用' : '已启用')
    fetchProductDetail()
  } catch (e) {
    // 错误已处理
  }
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除产品 "${product.value?.name}" 吗？`, '提示', {
      type: 'warning'
    })
    await deleteProduct(productId.value)
    ElMessage.success('删除成功')
    router.push('/products')
  } catch (e) {
    // 取消或错误
  }
}

onMounted(() => {
  fetchProductDetail()
})
</script>

<style lang="scss" scoped>
.product-detail {
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
      .product-name {
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

          &.price {
            font-size: 18px;
            font-weight: bold;
            color: #f56c6c;
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

    .product-image {
      width: 200px;
      height: 200px;
      margin-right: 16px;
      margin-bottom: 16px;
      cursor: pointer;
    }

    .detail-actions {
      margin-top: 40px;
      display: flex;
      gap: 12px;
    }
  }
}
</style>