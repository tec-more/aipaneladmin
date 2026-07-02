<template>
  <div class="aging-analysis-index">
    <el-card shadow="never" class="search-card">
      <template #header>
        <div class="card-header">
          <span>账龄分析</span>
        </div>
      </template>
      
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="类型">
          <el-select v-model="searchForm.type" placeholder="应收/应付" style="width: 120px">
            <el-option label="应收" value="receivable" />
            <el-option label="应付" value="payable" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户/供应商">
          <el-select v-model="searchForm.party_id" placeholder="全部" clearable filterable style="width: 200px">
            <el-option v-for="p in partyList" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="tableData" border stripe>
        <el-table-column prop="party_name" label="客户/供应商" min-width="150" />
        <el-table-column prop="total_amount" label="总金额" width="130" align="right">
          <template #default="{ row }">{{ Number(row.total_amount).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="age_0_30" label="0-30天" width="120" align="right">
          <template #default="{ row }">{{ Number(row.age_0_30 || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="age_31_60" label="31-60天" width="120" align="right">
          <template #default="{ row }">{{ Number(row.age_31_60 || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="age_61_90" label="61-90天" width="120" align="right">
          <template #default="{ row }">{{ Number(row.age_61_90 || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="age_91_180" label="91-180天" width="120" align="right">
          <template #default="{ row }">{{ Number(row.age_91_180 || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="age_180+" label="180天以上" width="120" align="right">
          <template #default="{ row }">{{ Number(row.age_180_plus || 0).toFixed(2) }}</template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[20, 50, 100]"
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

const tableData = ref([])
const partyList = ref([])
const loading = ref(false)

const searchForm = reactive({
  type: 'receivable',
  party_id: null
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  searchForm.type = 'receivable'
  searchForm.party_id = null
  pagination.page = 1
  fetchData()
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({ page: pagination.page, page_size: pagination.page_size, type: searchForm.type })
    if (searchForm.party_id) params.append('party_id', searchForm.party_id)
    
    const response = await fetch(`/api/v1/finance/aging-analysis?${params}`)
    const data = await response.json()
    
    if (response.ok) {
      tableData.value = data.data || []
      pagination.total = data.total || 0
    } else {
      tableData.value = []
      pagination.total = 0
    }
  } catch (error) {
    tableData.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

const fetchParties = async () => {
  try {
    const response = await fetch(searchForm.type === 'receivable' 
      ? '/api/v1/sales/customers/?page_size=100' 
      : '/api/v1/purchase/suppliers/?page_size=100')
    const data = await response.json()
    partyList.value = data.data || []
  } catch (error) {
    partyList.value = []
  }
}

onMounted(() => {
  fetchParties()
  fetchData()
})
</script>

<style lang="scss" scoped>
.aging-analysis-index {
  padding: 20px;
}
</style>


