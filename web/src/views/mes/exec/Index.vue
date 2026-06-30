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
import { Search, Refresh } from '@element-plus/icons-vue'
import { getProductionOrderList } from '@/api/mes'

const loading = ref(false)
const tableData = ref([])

const searchForm = reactive({
  order_code: '',
  status: null
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

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
    tableData.value = res.items || []
    pagination.total = res.total || 0
  } catch (e) { console.error('获取生产订单失败:', e) }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.page = 1; fetchData() }
const handleReset = () => { searchForm.order_code = ''; searchForm.status = null; handleSearch() }

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
