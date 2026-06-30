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
          <el-button type="primary" :icon="Plus">新建计划</el-button>
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import { getProductionPlanList } from '@/api/mes'

const loading = ref(false)
const tableData = ref([])

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
    tableData.value = res.items || []
    pagination.total = res.total || 0
  } catch (e) { console.error('获取生产计划失败:', e) }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.page = 1; fetchData() }
const handleReset = () => { searchForm.plan_code = ''; searchForm.product_name = ''; searchForm.status = null; handleSearch() }

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
