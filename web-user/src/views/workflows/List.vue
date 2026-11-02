<template>
  <!-- 我的工作流列表（M8：仅 own/linked）；T8 范围：分页/搜索/新建/删除 -->
  <div class="page-card">
    <div class="page-header">
      <h2 class="page-title">工作流</h2>
      <div class="page-actions">
        <el-input
          v-model="query.keyword"
          placeholder="搜索名称"
          :prefix-icon="Search"
          clearable
          style="width: 220px"
          @keyup.enter="loadList(1)"
          @clear="loadList(1)"
        />
        <el-button type="primary" :icon="Plus" @click="createVisible = true">新建工作流</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="list" class="page-table">
      <el-table-column prop="name" label="名称" min-width="180">
        <template #default="{ row }">
          <el-button text type="primary" @click="goEditor(row)">{{ row.name }}</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.description || '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status === 'published' ? 'success' : 'info'" effect="light">
            {{ row.status === 'published' ? '已发布' : '草稿' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="180">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="goEditor(row)">编辑</el-button>
          <el-button text type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无工作流，点击右上角新建" />
      </template>
    </el-table>

    <el-pagination
      v-model:current-page="query.page"
      :page-size="query.page_size"
      :total="total"
      layout="total, prev, pager, next"
      class="page-pagination"
      @current-change="loadList()"
    />

    <!-- 新建工作流（graph_json 缺省，后端生成 start→end 骨架） -->
    <el-dialog v-model="createVisible" title="新建工作流" width="440px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-position="top">
        <el-form-item label="名称" prop="name">
          <el-input v-model="createForm.name" maxlength="50" show-word-limit placeholder="请输入工作流名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" maxlength="200" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="onCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { getMyWorkflows, createWorkflow, deleteWorkflow } from '@/api/workflow'

const router = useRouter()

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10, keyword: '' })

async function loadList(page) {
  if (page) query.page = page
  loading.value = true
  try {
    const res = await getMyWorkflows({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined
    })
    // BUG-T15-006：统一包络解包（res?.data ?? res 兜底，对齐项目既有范式）
    const d = res?.data ?? res
    list.value = d?.items || []
    total.value = d?.total || 0
  } catch {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
}

function formatTime(t) {
  return t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '—'
}

function goEditor(row) {
  router.push({ name: 'WorkflowEditor', params: { id: row.id } })
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(
      `删除后草稿与发布版将一并清除且不可恢复，确认删除「${row.name}」？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', confirmButtonClass: 'el-button--danger' }
    )
  } catch {
    return
  }
  try {
    await deleteWorkflow(row.id)
    ElMessage.success('已删除')
    loadList()
  } catch {
    // 拦截器已提示
  }
}

// ---- 新建 ----
const createVisible = ref(false)
const creating = ref(false)
const createFormRef = ref()
const createForm = reactive({ name: '', description: '' })
const createRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }]
}

async function onCreate() {
  await createFormRef.value.validate()
  creating.value = true
  try {
    const res = await createWorkflow({ name: createForm.name, description: createForm.description })
    createVisible.value = false
    createForm.name = ''
    createForm.description = ''
    ElMessage.success('创建成功')
    // BUG-T15-006：统一包络解包
    const d = res?.data ?? res
    router.push({ name: 'WorkflowEditor', params: { id: d?.id } })
  } catch {
    // 拦截器已提示
  } finally {
    creating.value = false
  }
}

onMounted(() => loadList())
</script>

<style scoped lang="scss">
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.page-actions {
  display: flex;
  gap: 12px;
}

.page-pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
