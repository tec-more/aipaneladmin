<template>
  <div class="mes-quality">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="检验单号">
          <el-input v-model="searchForm.inspection_code" placeholder="请输入单号" clearable />
        </el-form-item>
        <el-form-item label="检验类型">
          <el-select v-model="searchForm.inspection_type" placeholder="请选择" clearable style="width: 120px">
            <el-option label="来料检验" value="incoming" />
            <el-option label="过程检验" value="process" />
            <el-option label="成品检验" value="finished" />
          </el-select>
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="searchForm.result" placeholder="请选择" clearable style="width: 100px">
            <el-option label="合格" value="passed" />
            <el-option label="不合格" value="failed" />
            <el-option label="待检" value="pending" />
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
          <span>质量检验列表</span>
          <el-button type="primary" :icon="Plus">新建检验单</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="inspection_code" label="检验单号" min-width="140" />
        <el-table-column prop="inspection_type" label="检验类型" width="100" align="center" />
        <el-table-column prop="product_name" label="产品名称" min-width="150" />
        <el-table-column prop="quantity" label="检验数量" width="100" align="center" />
        <el-table-column prop="passed_quantity" label="合格数量" width="100" align="center" />
        <el-table-column label="结果" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="resultTypeMap[row.result] || 'info'">
              {{ resultMap[row.result] || row.result }}
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
import { getQualityInspectionList } from '@/api/mes'

const loading = ref(false)
const tableData = ref([])

const searchForm = reactive({
  inspection_code: '',
  inspection_type: null,
  result: null
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const resultMap = {
  pending: '待检',
  passed: '合格',
  failed: '不合格'
}

const resultTypeMap = {
  pending: 'warning',
  passed: 'success',
  failed: 'danger'
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getQualityInspectionList({
      page: pagination.page,
      page_size: pagination.pageSize,
      ...searchForm
    })
    tableData.value = res.data?.items || []
    pagination.total = res.data?.total || 0
  } catch (e) { console.error('获取检验列表失败:', e) }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.page = 1; fetchData() }
const handleReset = () => { searchForm.inspection_code = ''; searchForm.inspection_type = null; searchForm.result = null; handleSearch() }

onMounted(() => { fetchData() })
</script>

<style lang="scss" scoped>
.mes-quality {
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
