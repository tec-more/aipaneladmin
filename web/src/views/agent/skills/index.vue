<template>
  <div class="skill-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>技能管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新增技能
          </el-button>
        </div>
      </template>
      
      <el-form :inline="true" :model="searchForm" class="mb-4">
        <el-form-item label="技能名称">
          <el-input v-model="searchForm.name" placeholder="请输入技能名称" clearable />
        </el-form-item>
        <el-form-item label="技能类型">
          <el-select v-model="searchForm.type" placeholder="请选择类型" clearable>
            <el-option label="工具调用" value="tool" />
            <el-option label="API调用" value="api" />
            <el-option label="数据处理" value="data" />
            <el-option label="条件判断" value="condition" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态" clearable>
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetSearch">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
      
      <el-table :data="skills" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="技能名称" min-width="120" />
        <el-table-column prop="type" label="技能类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.type)">{{ getTypeName(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button type="info" size="small" @click="handleTest(row)">
              <el-icon><VideoPlay /></el-icon>
              测试
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row.id)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="mt-4">
        <el-pagination
          v-model:current-page="pageInfo.currentPage"
          v-model:page-size="pageInfo.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="pageInfo.total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px">
      <el-form :model="formData" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="技能名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入技能名称" />
        </el-form-item>
        <el-form-item label="技能类型" prop="type">
          <el-select v-model="formData.type" placeholder="请选择技能类型" style="width: 100%">
            <el-option label="工具调用" value="tool" />
            <el-option label="API调用" value="api" />
            <el-option label="数据处理" value="data" />
            <el-option label="条件判断" value="condition" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="formData.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="formData.status" placeholder="请选择状态">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="参数配置">
          <el-input v-model="parametersJson" type="textarea" :rows="4" placeholder="JSON格式参数配置" />
        </el-form-item>
        <el-form-item label="实现代码">
          <el-input v-model="formData.implementation" type="textarea" :rows="6" placeholder="技能实现代码（Python）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="testDialogVisible" title="测试技能" width="600px">
      <el-form :model="testForm" label-width="100px">
        <el-form-item label="技能名称">
          <el-input :value="currentSkill?.name" disabled />
        </el-form-item>
        <el-form-item label="输入参数">
          <el-input v-model="testForm.input" type="textarea" :rows="4" placeholder="JSON格式输入参数" />
        </el-form-item>
        <el-form-item label="执行结果">
          <el-input v-model="testResult" type="textarea" :rows="4" readonly placeholder="执行结果" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="testDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="executeTest" :loading="testLoading">执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Refresh, Edit, Delete, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSkills, createSkill, updateSkill, deleteSkill, executeSkill } from '@/api/agent'

const router = useRouter()
const loading = ref(false)
const skills = ref([])

const searchForm = reactive({
  name: '',
  type: '',
  status: ''
})

const pageInfo = reactive({
  currentPage: 1,
  pageSize: 10,
  total: 0
})

const dialogVisible = ref(false)
const dialogTitle = ref('新增技能')
const formRef = ref(null)
const formData = reactive({
  id: null,
  name: '',
  type: 'tool',
  description: '',
  status: 'active',
  parameters: {},
  implementation: ''
})

const parametersJson = computed({
  get: () => JSON.stringify(formData.parameters, null, 2),
  set: (val) => {
    try {
      formData.parameters = JSON.parse(val)
    } catch (e) {}
  }
})

const rules = {
  name: [{ required: true, message: '请输入技能名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择技能类型', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

const testDialogVisible = ref(false)
const testLoading = ref(false)
const currentSkill = ref(null)
const testForm = reactive({ input: '{}' })
const testResult = ref('')

const typeMap = {
  tool: '工具调用',
  api: 'API调用',
  data: '数据处理',
  condition: '条件判断',
  other: '其他'
}

const getTypeName = (type) => typeMap[type] || type
const getTypeTagType = (type) => {
  const map = { tool: 'primary', api: 'success', data: 'warning', condition: 'info', other: '' }
  return map[type] || ''
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

const fetchSkills = async () => {
  loading.value = true
  try {
    const res = await getSkills({
      skip: (pageInfo.currentPage - 1) * pageInfo.pageSize,
      limit: pageInfo.pageSize,
      ...searchForm
    })
    if (res.data) {
      skills.value = res.data.items || res.data
      pageInfo.total = res.data.total || skills.value.length
    }
  } catch (error) {
    ElMessage.error('获取技能列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pageInfo.currentPage = 1
  fetchSkills()
}

const resetSearch = () => {
  searchForm.name = ''
  searchForm.type = ''
  searchForm.status = ''
  handleSearch()
}

const handleSizeChange = (size) => {
  pageInfo.pageSize = size
  fetchSkills()
}

const handleCurrentChange = (current) => {
  pageInfo.currentPage = current
  fetchSkills()
}

const handleAdd = () => {
  router.push('/panel/agent/skills/create')
}

const handleEdit = (row) => {
  router.push(`/panel/agent/skills/edit/${row.id}`)
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (formData.id) {
          await updateSkill(formData.id, formData)
          ElMessage.success('编辑成功')
        } else {
          await createSkill(formData)
          ElMessage.success('新增成功')
        }
        dialogVisible.value = false
        fetchSkills()
      } catch (error) {
        ElMessage.error('操作失败')
        console.error(error)
      }
    }
  })
}

const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除该技能吗？', '提示', { type: 'warning' })
    await deleteSkill(id)
    ElMessage.success('删除成功')
    fetchSkills()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

const handleTest = (row) => {
  currentSkill.value = row
  testForm.input = JSON.stringify(row.parameters || {}, null, 2)
  testResult.value = ''
  testDialogVisible.value = true
}

const executeTest = async () => {
  testLoading.value = true
  try {
    let input = {}
    try {
      input = JSON.parse(testForm.input)
    } catch (e) {
      ElMessage.error('输入参数格式错误')
      return
    }
    const res = await executeSkill(currentSkill.value.id, input)
    testResult.value = JSON.stringify(res.data, null, 2)
    ElMessage.success('执行成功')
  } catch (error) {
    testResult.value = error.message || '执行失败'
    ElMessage.error('执行失败')
  } finally {
    testLoading.value = false
  }
}

onMounted(() => {
  fetchSkills()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.mb-4 {
  margin-bottom: 16px;
}
.mt-4 {
  margin-top: 16px;
}
</style>
