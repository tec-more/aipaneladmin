<template>
  <div class="mes-equipment">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="设备编号">
          <el-input v-model="searchForm.equipment_code" placeholder="请输入编号" clearable />
        </el-form-item>
        <el-form-item label="设备名称">
          <el-input v-model="searchForm.name" placeholder="请输入名称" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择" clearable style="width: 120px">
            <el-option label="运行中" value="running" />
            <el-option label="待机" value="idle" />
            <el-option label="维修中" value="maintenance" />
            <el-option label="停用" value="disabled" />
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
          <span>设备列表</span>
          <el-button type="primary" :icon="Plus">新增设备</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="equipment_code" label="设备编号" min-width="120" />
        <el-table-column prop="name" label="设备名称" min-width="150" />
        <el-table-column prop="specification" label="规格型号" min-width="150" />
        <el-table-column prop="location" label="所在位置" min-width="120" />
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
import { getEquipmentList } from '@/api/mes'

const loading = ref(false)
const tableData = ref([])

const searchForm = reactive({
  equipment_code: '',
  name: '',
  status: null
})

const pagination = reactive({ page: 1, pageSize: 10, total: 0 })

const statusMap = {
  running: '运行中',
  idle: '待机',
  maintenance: '维修中',
  disabled: '停用'
}

const statusTypeMap = {
  running: 'success',
  idle: 'info',
  maintenance: 'warning',
  disabled: 'danger'
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getEquipmentList({
      page: pagination.page,
      page_size: pagination.pageSize,
      ...searchForm
    })
    tableData.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (e) { console.error('获取设备列表失败:', e) }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.page = 1; fetchData() }
const handleReset = () => { searchForm.equipment_code = ''; searchForm.name = ''; searchForm.status = null; handleSearch() }

onMounted(() => { fetchData() })
</script>

<style lang="scss" scoped>
.mes-equipment {
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
