<template>
  <div class="document-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>文档列表</span>
          <div class="header-actions">
            <el-input
              v-model="searchTitle"
              placeholder="搜索文档标题"
              :prefix-icon="Search"
              clearable
              style="width: 240px; margin-right: 12px;"
              @keyup.enter="handleSearch"
            />
            <el-select
              v-model="filterCategory"
              placeholder="全部分类"
              clearable
              style="width: 160px; margin-right: 12px;"
            >
              <el-option
                v-for="cat in categoryOptions"
                :key="cat.id"
                :label="cat.name"
                :value="cat.id"
              />
            </el-select>
            <el-button type="primary" :icon="Refresh" @click="handleSearch">
              查询
            </el-button>
            <el-button :icon="Plus" type="success" @click="showUploadDialog = true">
              上传文档
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="tableData"
        v-loading="loading"
        stripe
        border
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="title" label="文档标题" min-width="200" />
        <el-table-column prop="file_name" label="文件名" min-width="150" />
        <el-table-column prop="file_type" label="类型" width="80" />
        <el-table-column prop="version" label="版本" width="70" />
        <el-table-column prop="visibility" label="可见性" width="80">
          <template #default="{ row }">
            <el-tag :type="row.visibility === 'public' ? 'success' : 'info'">
              {{ row.visibility === 'public' ? '公开' : row.visibility === 'dept' ? '部门' : '私有' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleView(row)">
              查看
            </el-button>
            <el-button link type="primary" size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="fetchList"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <!-- 上传对话框 -->
    <el-dialog v-model="showUploadDialog" title="上传文档" width="500px">
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="文件">
          <el-upload
            v-model:file-list="uploadForm.fileList"
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
          >
            <el-button type="primary" :icon="Upload">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">支持 PDF、Word、Excel、图片等格式</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="uploadForm.title" placeholder="留空则使用文件名" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="uploadForm.category_id" placeholder="选择分类" clearable>
            <el-option
              v-for="cat in categoryOptions"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="可见性">
          <el-select v-model="uploadForm.visibility">
            <el-option label="私有" value="private" />
            <el-option label="部门" value="dept" />
            <el-option label="公开" value="public" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="uploadForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploading">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Upload } from '@element-plus/icons-vue'
import {
  getDocumentList,
  getCategoryTree,
  uploadDocument,
  deleteDocument
} from '@/api/document'

const loading = ref(false)
const uploading = ref(false)
const tableData = ref([])
const searchTitle = ref('')
const filterCategory = ref(null)
const categoryOptions = ref([])
const showUploadDialog = ref(false)

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const uploadForm = reactive({
  fileList: [],
  title: '',
  category_id: null,
  visibility: 'private',
  description: '',
  file: null
})

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const handleFileChange = (file) => {
  uploadForm.file = file.raw
}

const fetchList = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }
    if (searchTitle.value) params.title = searchTitle.value
    if (filterCategory.value) params.category_id = filterCategory.value
    
    const res = await getDocumentList(params)
    if (res.code === 0) {
      tableData.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (e) {
    ElMessage.error('获取文档列表失败')
  } finally {
    loading.value = false
  }
}

const fetchCategories = async () => {
  try {
    const res = await getCategoryTree()
    if (res.code === 0) {
      const flatList = []
      const flatten = (items) => {
        items.forEach(item => {
          flatList.push({ id: item.id, name: item.name })
          if (item.children && item.children.length) flatten(item.children)
        })
      }
      flatten(res.data)
      categoryOptions.value = flatList
    }
  } catch (e) {
    console.error('获取分类失败:', e)
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchList()
}

const handleUpload = async () => {
  if (!uploadForm.file) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadForm.file)
    if (uploadForm.title) formData.append('title', uploadForm.title)
    if (uploadForm.category_id) formData.append('category_id', uploadForm.category_id)
    if (uploadForm.description) formData.append('description', uploadForm.description)
    formData.append('visibility', uploadForm.visibility)
    
    const res = await uploadDocument(formData)
    if (res.code === 0) {
      ElMessage.success('上传成功')
      showUploadDialog.value = false
      resetUploadForm()
      fetchList()
    } else {
      ElMessage.error(res.msg || '上传失败')
    }
  } catch (e) {
    ElMessage.error('上传失败: ' + e.message)
  } finally {
    uploading.value = false
  }
}

const resetUploadForm = () => {
  uploadForm.fileList = []
  uploadForm.title = ''
  uploadForm.category_id = null
  uploadForm.visibility = 'private'
  uploadForm.description = ''
  uploadForm.file = null
}

const handleView = (row) => {
  window.open(`/v1/document/preview/${row.id}`, '_blank')
}

const handleEdit = (row) => {
  ElMessage.info('编辑功能开发中')
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除文档「${row.title}」吗？`, '确认删除', {
      type: 'warning'
    })
    const res = await deleteDocument(row.id)
    if (res.code === 0) {
      ElMessage.success('删除成功')
      fetchList()
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  fetchList()
  fetchCategories()
})
</script>

<style lang="scss" scoped>
.document-list {
  padding: 20px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .header-actions {
    display: flex;
    align-items: center;
  }
  
  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
  
  .el-upload__tip {
    color: var(--el-text-color-secondary);
    font-size: 12px;
    margin-top: 4px;
  }
}
</style>
