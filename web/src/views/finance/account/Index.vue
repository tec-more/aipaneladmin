<template>
  <div class="account-index">
    <div class="page-header">
      <h2>会计科目</h2>
      <div class="header-actions">
        <button @click="loadAccountTypes" class="btn btn-outline">科目类型</button>
        <button @click="handleAdd" class="btn btn-primary">新增科目</button>
      </div>
    </div>
    
    <div class="search-bar">
      <input v-model="searchForm.keyword" placeholder="搜索科目名称或编码" @keyup.enter="handleSearch" />
      <select v-model="searchForm.account_type">
        <option value="">全部类型</option>
        <option v-for="type in accountTypes" :key="type.value" :value="type.value">{{ type.label }}</option>
      </select>
      <button @click="handleSearch" class="btn btn-primary">搜索</button>
      <button @click="handleReset" class="btn btn-outline">重置</button>
    </div>
    
    <div class="table-container">
      <el-table :data="tableData" border>
        <el-table-column prop="code" label="科目编码" />
        <el-table-column prop="name" label="科目名称" />
        <el-table-column prop="account_type" label="科目类型">
          <template #default="{ row }">
            {{ getAccountTypeName(row.account_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="parent_name" label="上级科目" />
        <el-table-column prop="balance" label="余额" />
        <el-table-column prop="is_active" label="状态">
          <template #default="{ row }">
            <span :class="row.is_active ? 'status-active' : 'status-inactive'">
              {{ row.is_active ? '启用' : '禁用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="{ row }">
            <button @click="handleEdit(row)" class="btn btn-sm btn-outline">编辑</button>
            <button @click="handleDelete(row)" class="btn btn-sm btn-danger">删除</button>
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
    
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="formData" label-width="100px">
        <el-form-item label="科目编码">
          <el-input v-model="formData.code" />
        </el-form-item>
        <el-form-item label="科目名称">
          <el-input v-model="formData.name" />
        </el-form-item>
        <el-form-item label="科目类型">
          <el-select v-model="formData.account_type">
            <el-option v-for="type in accountTypes" :key="type.value" :label="type.label" :value="type.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="上级科目">
          <el-select v-model="formData.parent_id">
            <el-option :label="''" :value="null" />
            <el-option v-for="acc in accountList" :key="acc.id" :label="acc.code + ' ' + acc.name" :value="acc.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="formData.description" type="textarea" />
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
import { useRouter } from 'vue-router'

const router = useRouter()
const tableData = ref([])
const accountTypes = ref([])
const accountList = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('新增科目')
const isEdit = ref(false)
const currentId = ref(null)

const searchForm = reactive({
  keyword: '',
  account_type: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const formData = reactive({
  code: '',
  name: '',
  account_type: '',
  parent_id: null,
  description: ''
})

const getAccountTypeName = (type) => {
  const found = accountTypes.value.find(t => t.value === type)
  return found ? found.label : type
}

const handleSearch = async () => {
  pagination.page = 1
  await fetchData()
}

const handleReset = () => {
  searchForm.keyword = ''
  searchForm.account_type = ''
  handleSearch()
}

const handlePageChange = (page) => {
  pagination.page = page
  fetchData()
}

const handleAdd = () => {
  isEdit.value = false
  currentId.value = null
  dialogTitle.value = '新增科目'
  Object.assign(formData, {
    code: '',
    name: '',
    account_type: '',
    parent_id: null,
    description: ''
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  currentId.value = row.id
  dialogTitle.value = '编辑科目'
  Object.assign(formData, {
    code: row.code,
    name: row.name,
    account_type: row.account_type,
    parent_id: row.parent_id,
    description: row.description || ''
  })
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  if (confirm(`确定删除科目 ${row.name} 吗？`)) {
    const response = await fetch(`/api/finance/accounts/${row.id}`, {
      method: 'DELETE'
    })
    const data = await response.json()
    if (data.code === 0) {
      alert(data.msg)
      fetchData()
    } else {
      alert(data.msg || '删除失败')
    }
  }
}

const handleSave = async () => {
  if (!formData.code || !formData.name || !formData.account_type) {
    alert('请填写必填项')
    return
  }
  
  const url = isEdit.value ? `/api/finance/accounts/${currentId.value}` : '/api/finance/accounts/'
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

const loadAccountTypes = async () => {
  const response = await fetch('/api/finance/accounts/types')
  const data = await response.json()
  if (data.code === 0) {
    accountTypes.value = data.data
  }
}

const fetchData = async () => {
  const params = new URLSearchParams({
    page: pagination.page,
    page_size: pagination.page_size,
    keyword: searchForm.keyword,
    account_type: searchForm.account_type
  })
  
  const response = await fetch(`/api/finance/accounts/?${params}`)
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
  loadAccountTypes()
  fetchData()
  fetchAccountList()
})
</script>

<style lang="scss" scoped>
.account-index {
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
  
  .header-actions {
    display: flex;
    gap: 10px;
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
  
  .status-active {
    color: #67c23a;
    font-weight: bold;
  }
  
  .status-inactive {
    color: #909399;
  }
}
</style>