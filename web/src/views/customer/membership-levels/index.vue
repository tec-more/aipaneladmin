<template>
  <div class="membership-levels-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>会员等级配置</span>
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新增等级
          </el-button>
        </div>
      </template>

      <!-- 筛选区 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="等级名称">
          <el-input v-model="searchForm.name" placeholder="请输入等级名称" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.is_active" placeholder="请选择状态" clearable>
            <el-option label="全部" :value="null" />
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchData">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 数据表格 -->
      <el-table :data="tableData" style="width: 100%" v-loading="loading" border>
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="name" label="等级名称" width="140" />
        <el-table-column prop="level_type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getLevelTypeColor(row.level_type)" size="small">
              {{ getLevelTypeName(row.level_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="level" label="等级" width="70" align="center" />
        <el-table-column prop="duration_days" label="有效期" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.duration_days > 0">{{ row.duration_days }}天</span>
            <span v-else style="color: #909399;">永久</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration_hours" label="小时数" width="80" align="center">
          <template #default="{ row }">
            {{ row.duration_hours || 0 }}h
          </template>
        </el-table-column>
        <el-table-column prop="bonus_hours" label="赠送" width="70" align="center">
          <template #default="{ row }">
            <span v-if="row.bonus_hours > 0" style="color: #67C23A;">+{{ row.bonus_hours }}h</span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="总小时数" width="110" align="center">
          <template #default="{ row }">
            <span style="color: #409EFF; font-weight: bold;">
              {{ (row.duration_hours || 0) + (row.bonus_hours || 0) }}h
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="120" align="center">
          <template #default="{ row }">
            <div style="color: #F56C6C; font-weight: bold; font-size: 16px;">
              ¥{{ row.price }}
            </div>
            <div v-if="row.original_price && row.original_price > row.price"
                 style="color: #909399; font-size: 11px; text-decoration: line-through;">
              ¥{{ row.original_price }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="折扣" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.discount_percentage > 0" type="danger" effect="plain" size="small">
              {{ row.discount_percentage }}% OFF
            </el-tag>
            <el-tag v-else-if="row.original_price && row.original_price > row.price" type="warning" effect="plain" size="small">
              {{ Math.round((1 - row.price / row.original_price) * 100) }}% OFF
            </el-tag>
            <span v-else style="color: #909399; font-size: 12px;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="70" align="center" />
        <el-table-column prop="features" label="特权" width="200" align="center">
          <template #default="{ row }">
            <el-tag
              v-for="(feature, index) in (row.features || []).slice(0, 2)"
              :key="index"
              size="small"
              style="margin: 2px;"
            >
              {{ feature }}
            </el-tag>
            <el-tooltip v-if="row.features && row.features.length > 2" :content="row.features.join(', ')">
              <el-tag size="small" type="info" style="margin: 2px;">
                +{{ row.features.length - 2 }}
              </el-tag>
            </el-tooltip>
            <span v-if="!row.features || row.features.length === 0" style="color: #909399; font-size: 12px;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
        <el-table-column prop="is_active" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button
              :type="row.is_active ? 'warning' : 'success'"
              size="small"
              @click="handleToggleStatus(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchData"
        @current-change="fetchData"
      />
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="等级名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入等级名称" />
        </el-form-item>
        <el-form-item label="等级" prop="level">
          <el-input-number v-model="form.level" :min="1" :max="20" placeholder="请输入等级" />
        </el-form-item>
        <el-form-item label="小时数" prop="duration_hours">
          <el-input-number v-model="form.duration_hours" :min="0" placeholder="请输入小时数" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            套餐包含的基础时长（年度会员可设为0）
          </div>
        </el-form-item>
        <el-form-item label="赠送小时" prop="bonus_hours">
          <el-input-number v-model="form.bonus_hours" :min="0" placeholder="请输入赠送小时数" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            购买时额外赠送的时长（计入总小时数）
          </div>
        </el-form-item>
        <el-form-item label="总小时数">
          <div style="padding: 8px 12px; background: #F5F7FA; border-radius: 4px; color: #409EFF; font-weight: bold;">
            {{ (form.duration_hours || 0) + (form.bonus_hours || 0) }}h
            <span style="color: #909399; font-weight: normal; font-size: 12px; margin-left: 8px;">
              (基础: {{ form.duration_hours || 0 }} + 赠送: {{ form.bonus_hours || 0 }})
            </span>
          </div>
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input-number v-model="form.price" :min="0" :precision="2" placeholder="请输入价格" style="width: 100%;" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            实际售价
          </div>
        </el-form-item>
        <el-form-item label="原价" prop="original_price">
          <el-input-number v-model="form.original_price" :min="0" :precision="2" placeholder="请输入原价（可选）" style="width: 100%;" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            用于显示划线价效果（留空则不显示原价）
          </div>
        </el-form-item>
        <el-form-item label="折扣(%)" prop="discount_percentage">
          <el-input-number
            v-model="form.discount_percentage"
            :min="0"
            :max="100"
            placeholder="手动设置折扣百分比"
            style="width: 100%;"
          />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            手动设置折扣，优先显示此折扣值（0表示不显示折扣）
          </div>
        </el-form-item>
        <el-form-item label="折扣预览">
          <div v-if="form.discount_percentage > 0" style="padding: 8px 12px; background: #FEF0F0; border-radius: 4px;">
            <span style="color: #F56C6C; font-weight: bold; font-size: 18px;">
              ¥{{ form.price }}
            </span>
            <span v-if="form.original_price && form.original_price > form.price" style="color: #909399; text-decoration: line-through; margin-left: 8px;">
              ¥{{ form.original_price }}
            </span>
            <el-tag type="danger" effect="plain" size="small" style="margin-left: 8px;">
              {{ form.discount_percentage }}% OFF
            </el-tag>
            <div style="font-size: 11px; color: #F56C6C; margin-top: 4px;">
              ⭐ 手动设置折扣
            </div>
          </div>
          <div v-else-if="form.original_price && form.original_price > form.price" style="padding: 8px 12px; background: #FEF0F0; border-radius: 4px;">
            <span style="color: #F56C6C; font-weight: bold; font-size: 18px;">
              ¥{{ form.price }}
            </span>
            <span style="color: #909399; text-decoration: line-through; margin-left: 8px;">
              ¥{{ form.original_price }}
            </span>
            <el-tag type="warning" effect="plain" size="small" style="margin-left: 8px;">
              {{ Math.round((1 - form.price / form.original_price) * 100) }}% OFF
            </el-tag>
            <div style="font-size: 11px; color: #E6A23C; margin-top: 4px;">
              ⚠️ 根据原价自动计算折扣
            </div>
          </div>
          <div v-else style="padding: 8px 12px; background: #F5F7FA; border-radius: 4px; color: #909399;">
            无折扣（价格: ¥{{ form.price }}）
          </div>
        </el-form-item>
        <el-form-item label="有效期天数" prop="duration_days">
          <el-input-number v-model="form.duration_days" :min="0" placeholder="请输入有效期天数" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            年度会员填365，月度填30，0表示永久
          </div>
        </el-form-item>
        <el-form-item label="等级类型" prop="level_type">
          <el-select v-model="form.level_type" placeholder="请选择等级类型" style="width: 100%;">
            <el-option label="体验会员" value="trial" />
            <el-option label="月度会员" value="monthly" />
            <el-option label="季度会员" value="quarterly" />
            <el-option label="半年会员" value="half_yearly" />
            <el-option label="年度会员" value="yearly" />
            <el-option label="终身会员" value="lifetime" />
            <el-option label="小时充值" value="fibonacci" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="form.sort_order" :min="0" placeholder="排序号（数字越小越靠前）" />
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入等级描述（选填）" />
        </el-form-item>
        <el-form-item label="特权列表" prop="features">
          <el-select
            v-model="form.features"
            multiple
            filterable
            allow-create
            placeholder="输入特权后按回车添加，或从下拉选择"
            style="width: 100%;"
          >
            <el-option label="无限翻译" value="无限翻译" />
            <el-option label="API访问" value="API访问" />
            <el-option label="离线翻译" value="离线翻译" />
            <el-option label="优先客服" value="优先客服" />
            <el-option label="专属客服" value="专属客服" />
            <el-option label="批量翻译" value="批量翻译" />
            <el-option label="多语言互译" value="多语言互译" />
            <el-option label="定制化主题" value="定制化主题" />
            <el-option label="去广告" value="去广告" />
            <el-option label="多账号管理" value="多账号管理" />
            <el-option label="团队协作" value="团队协作" />
            <el-option label="7x24客服" value="7x24客服" />
          </el-select>
          <div style="font-size: 12px; color: #909399; margin-top: 4px;">
            已选择 {{ form.features?.length || 0 }} 项特权
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getMembershipLevels, createMembershipLevel, updateMembershipLevel, deleteMembershipLevel } from '@/api/customer'

// 响应式数据
const loading = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('新增等级')
const formRef = ref()

const searchForm = reactive({
  name: '',
  is_active: null
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const form = reactive({
  id: null,
  name: '',
  level_type: 'fibonacci',
  level: 1,
  description: '',
  duration_days: 30,
  duration_hours: 0,
  price: 0,
  original_price: null,
  bonus_hours: 0,
  discount_percentage: 0,
  features: [],
  sort_order: 0,
  is_active: true
})

const rules = {
  name: [{ required: true, message: '请输入等级名称', trigger: 'blur' }],
  level_type: [{ required: true, message: '请选择等级类型', trigger: 'change' }],
  level: [{ required: true, message: '请输入等级', trigger: 'blur' }],
  duration_days: [{ required: true, message: '请输入有效期天数', trigger: 'blur' }],
  price: [{ required: true, message: '请输入价格', trigger: 'blur' }]
}

// 方法
const fetchData = async () => {
  loading.value = true
  try {
    const res = await getMembershipLevels({
      page: pagination.page,
      page_size: pagination.pageSize,
      name: searchForm.name || undefined,
      is_active: searchForm.is_active
    })
    tableData.value = res.data.items || res.data || []
    pagination.total = res.data.total || 0
  } catch (e) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  searchForm.name = ''
  searchForm.is_active = null
  fetchData()
}

const handleCreate = () => {
  dialogTitle.value = '新增等级'
  Object.assign(form, {
    id: null,
    name: '',
    level_type: 'fibonacci',
    level: 1,
    description: '',
    duration_days: 30,
    duration_hours: 0,
    price: 0,
    original_price: null,
    bonus_hours: 0,
    discount_percentage: 0,
    features: [],
    sort_order: 0,
    is_active: true
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑等级'
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleSubmit = async () => {
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      if (form.id) {
        await updateMembershipLevel(form.id, form)
        ElMessage.success('更新成功')
      } else {
        await createMembershipLevel(form)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      fetchData()
    } catch (e) {
      ElMessage.error('操作失败')
    }
  })
}

const handleToggleStatus = async (row) => {
  try {
    await updateMembershipLevel(row.id, { is_active: !row.is_active })
    ElMessage.success('状态切换成功')
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该等级吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteMembershipLevel(row.id)
      ElMessage.success('删除成功')
      fetchData()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  })
}

const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

// 获取等级类型中文名
const getLevelTypeName = (type) => {
  const typeMap = {
    'trial': '体验',
    'monthly': '月度',
    'quarterly': '季度',
    'half_yearly': '半年',
    'yearly': '年度',
    'lifetime': '终身',
    'fibonacci': '小时'
  }
  return typeMap[type] || type
}

// 获取等级类型颜色
const getLevelTypeColor = (type) => {
  const colorMap = {
    'trial': '',
    'monthly': 'success',
    'quarterly': 'info',
    'half_yearly': 'warning',
    'yearly': 'danger',
    'lifetime': 'danger',
    'fibonacci': 'primary'
  }
  return colorMap[type] || ''
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.membership-levels-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
}
</style>
