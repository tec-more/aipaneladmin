<template>
  <div class="journal-index">
    <div class="page-header">
      <h2>凭证管理</h2>
      <div class="header-actions">
        <button @click="handleAdd" class="btn btn-primary">新增凭证</button>
      </div>
    </div>
    
    <div class="search-bar">
      <select v-model="searchForm.journal_type">
        <option value="">全部类型</option>
        <option v-for="type in journalTypes" :key="type.value" :value="type.value">{{ type.label }}</option>
      </select>
      <select v-model="searchForm.status">
        <option value="">全部状态</option>
        <option v-for="status in journalStatuses" :key="status.value" :value="status.value">{{ status.label }}</option>
      </select>
      <input v-model="searchForm.journal_date_start" type="date" />
      <input v-model="searchForm.journal_date_end" type="date" />
      <button @click="handleSearch" class="btn btn-primary">搜索</button>
      <button @click="handleReset" class="btn btn-outline">重置</button>
    </div>
    
    <div class="table-container">
      <el-table :data="tableData" border>
        <el-table-column prop="journal_number" label="凭证号" />
        <el-table-column prop="journal_type" label="凭证类型">
          <template #default="{ row }">
            {{ getJournalTypeName(row.journal_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="journal_date" label="凭证日期" />
        <el-table-column prop="period" label="会计期间" />
        <el-table-column prop="description" label="摘要" />
        <el-table-column prop="total_debit" label="借方金额" />
        <el-table-column prop="total_credit" label="贷方金额" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <span :class="getStatusClass(row.status)">{{ getStatusName(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_by" label="制单" />
        <el-table-column prop="confirmed_by" label="审核" />
        <el-table-column label="操作">
          <template #default="{ row }">
            <button @click="handleEdit(row)" class="btn btn-sm btn-outline">编辑</button>
            <button v-if="row.status === 'draft'" @click="handleConfirm(row)" class="btn btn-sm btn-primary">审核</button>
            <button v-if="row.status === 'confirmed'" @click="handlePost(row)" class="btn btn-sm btn-success">过账</button>
            <button v-if="row.status !== 'cancelled'" @click="handleCancel(row)" class="btn btn-sm btn-danger">取消</button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        :current-page="pagination.page"
        :page-size="pagination.page_size"
        :total="pagination.total"
        @current-change="handlePageChange"
        layout="total, prev, pager, next"
      />
    </div>
    
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px">
      <el-form :model="formData" label-width="80px">
        <el-form-item label="凭证类型">
          <el-select v-model="formData.journal_type">
            <el-option v-for="type in journalTypes" :key="type.value" :label="type.label" :value="type.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="凭证日期">
          <el-date-picker v-model="formData.journal_date" type="date" />
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="formData.description" />
        </el-form-item>
        <el-form-item label="凭证行">
          <div v-for="(line, index) in formData.lines" :key="index" class="journal-line">
            <el-select v-model="line.account_id" placeholder="科目">
              <el-option v-for="acc in accountList" :key="acc.id" :label="acc.code + ' ' + acc.name" :value="acc.id" />
            </el-select>
            <el-input v-model="line.debit" type="number" placeholder="借方" />
            <el-input v-model="line.credit" type="number" placeholder="贷方" />
            <el-input v-model="line.description" placeholder="明细摘要" />
            <button v-if="formData.lines.length > 1" @click="removeLine(index)" class="btn btn-sm btn-danger">删除</button>
          </div>
          <button @click="addLine" class="btn btn-sm btn-outline">添加行</button>
        </el-form-item>
      </el-form>
      <template #footer>
        <button @click="dialogVisible = false" class="btn btn-outline">取消</button>
        <button @click="handleSave" class="btn btn-primary">保存</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'

const tableData = ref([])
const journalTypes = ref([])
const journalStatuses = ref([])
const accountList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('新增凭证')
const isEdit = ref(false)
const currentId = ref(null)

const searchForm = reactive({
  journal_type: '',
  status: '',
  journal_date_start: '',
  journal_date_end: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const formData = reactive({
  journal_type: 'general',
  journal_date: '',
  description: '',
  lines: [{ account_id: null, debit: '', credit: '', description: '' }]
})

const getJournalTypeName = (type) => {
  const found = journalTypes.value.find(t => t.value === type)
  return found ? found.label : type
}

const getStatusName = (status) => {
  const found = journalStatuses.value.find(s => s.value === status)
  return found ? found.label : status
}

const getStatusClass = (status) => {
  const classes = {
    'draft': 'status-draft',
    'confirmed': 'status-confirmed',
    'posted': 'status-posted',
    'cancelled': 'status-cancelled'
  }
  return classes[status] || ''
}

const handleSearch = async () => {
  pagination.page = 1
  await fetchData()
}

const handleReset = () => {
  searchForm.journal_type = ''
  searchForm.status = ''
  searchForm.journal_date_start = ''
  searchForm.journal_date_end = ''
  handleSearch()
}

const handlePageChange = (page) => {
  pagination.page = page
  fetchData()
}

const handleAdd = () => {
  isEdit.value = false
  currentId.value = null
  dialogTitle.value = '新增凭证'
  Object.assign(formData, {
    journal_type: 'general',
    journal_date: new Date().toISOString().split('T')[0],
    description: '',
    lines: [{ account_id: null, debit: '', credit: '', description: '' }]
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  currentId.value = row.id
  dialogTitle.value = '编辑凭证'
  Object.assign(formData, {
    journal_type: row.journal_type,
    journal_date: row.journal_date,
    description: row.description,
    lines: row.lines || [{ account_id: null, debit: '', credit: '', description: '' }]
  })
  dialogVisible.value = true
}

const addLine = () => {
  formData.lines.push({ account_id: null, debit: '', credit: '', description: '' })
}

const removeLine = (index) => {
  formData.lines.splice(index, 1)
}

const handleConfirm = async (row) => {
  if (confirm('确定审核该凭证吗？')) {
    const response = await fetch(`/api/finance/journals/${row.id}/confirm`, {
      method: 'POST'
    })
    const data = await response.json()
    if (data.code === 0) {
      alert(data.msg)
      fetchData()
    } else {
      alert(data.msg || '审核失败')
    }
  }
}

const handlePost = async (row) => {
  if (confirm('确定过账该凭证吗？')) {
    const response = await fetch(`/api/finance/journals/${row.id}/post`, {
      method: 'POST'
    })
    const data = await response.json()
    if (data.code === 0) {
      alert(data.msg)
      fetchData()
    } else {
      alert(data.msg || '过账失败')
    }
  }
}

const handleCancel = async (row) => {
  if (confirm('确定取消该凭证吗？')) {
    const response = await fetch(`/api/finance/journals/${row.id}/cancel`, {
      method: 'POST'
    })
    const data = await response.json()
    if (data.code === 0) {
      alert(data.msg)
      fetchData()
    } else {
      alert(data.msg || '取消失败')
    }
  }
}

const handleSave = async () => {
  if (!formData.journal_type || !formData.journal_date) {
    alert('请填写必填项')
    return
  }
  
  const url = isEdit.value ? `/api/finance/journals/${currentId.value}` : '/api/finance/journals/'
  const method = isEdit.value ? 'PUT' : 'POST'
  
  const response = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
  })
  
  const data = await response.json()
  if (data.code === 0 || response.ok) {
    alert('保存成功')
    dialogVisible.value = false
    fetchData()
  } else {
    alert(data.msg || '保存失败')
  }
}

const loadJournalTypes = async () => {
  const response = await fetch('/api/finance/journals/types')
  const data = await response.json()
  if (data.code === 0) {
    journalTypes.value = data.data
  }
}

const loadJournalStatuses = async () => {
  const response = await fetch('/api/finance/journals/statuses')
  const data = await response.json()
  if (data.code === 0) {
    journalStatuses.value = data.data
  }
}

const fetchData = async () => {
  const params = new URLSearchParams({
    page: pagination.page,
    page_size: pagination.page_size,
    journal_type: searchForm.journal_type,
    status: searchForm.status,
    journal_date_start: searchForm.journal_date_start,
    journal_date_end: searchForm.journal_date_end
  })
  
  const response = await fetch(`/api/finance/journals/?${params}`)
  const data = await response.json()
  
  if (data.code === 0) {
    tableData.value = data.data
    pagination.total = data.total
    pagination.page = data.page
    pagination.page_size = data.page_size
  } else {
    tableData.value = data.data || []
    pagination.total = data.total || 0
  }
}

const fetchAccountList = async () => {
  const response = await fetch('/api/finance/accounts/?page_size=1000')
  const data = await response.json()
  if (data.code === 0) {
    accountList.value = data.data
  } else {
    accountList.value = data.data || []
  }
}

onMounted(() => {
  loadJournalTypes()
  loadJournalStatuses()
  fetchData()
  fetchAccountList()
})
</script>

<style lang="scss" scoped>
.journal-index {
  padding: 20px;
  
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h2 {
      margin: 0;
    }
  }
  
  .search-bar {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    
    input, select {
      padding: 8px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
    }
  }
  
  .table-container {
    background: white;
    border-radius: 8px;
    padding: 20px;
    
    .el-pagination {
      margin-top: 20px;
      text-align: right;
    }
  }
  
  .journal-line {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
    align-items: center;
    
    select, input {
      padding: 8px;
      border: 1px solid #ddd;
      border-radius: 4px;
    }
  }
  
  .status-draft {
    color: #909399;
  }
  
  .status-confirmed {
    color: #409eff;
    font-weight: bold;
  }
  
  .status-posted {
    color: #67c23a;
    font-weight: bold;
  }
  
  .status-cancelled {
    color: #f56c6c;
    text-decoration: line-through;
  }
}
</style>