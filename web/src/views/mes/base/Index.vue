<template>
  <div class="mes-base">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="物料管理" name="material">
        <el-card shadow="never" class="search-card">
          <el-form :inline="true" :model="materialSearch" class="search-form">
            <el-form-item label="物料编码">
              <el-input v-model="materialSearch.material_code" placeholder="请输入编码" clearable />
            </el-form-item>
            <el-form-item label="物料名称">
              <el-input v-model="materialSearch.name" placeholder="请输入名称" clearable />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Search" @click="fetchMaterialList">搜索</el-button>
              <el-button :icon="Refresh" @click="resetMaterialSearch">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
        <el-card shadow="never" class="table-card">
          <template #header>
            <div class="card-header">
              <span>物料列表</span>
              <el-button type="primary" :icon="Plus" @click="handleAddMaterial">新增物料</el-button>
            </div>
          </template>
          <el-table v-loading="materialLoading" :data="materialList" border stripe>
            <el-table-column prop="id" label="ID" width="80" align="center" />
            <el-table-column prop="material_code" label="物料编码" min-width="120" />
            <el-table-column prop="name" label="物料名称" min-width="150" />
            <el-table-column prop="specification" label="规格" min-width="150" />
            <el-table-column prop="unit" label="单位" width="80" align="center" />
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180" />
            <el-table-column label="操作" width="150" fixed="right" align="center">
              <template #default="{ row }">
                <el-button type="primary" link :icon="Edit" @click="handleEditMaterial(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="materialPagination.page"
              v-model:page-size="materialPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="materialPagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="fetchMaterialList"
              @current-change="fetchMaterialList"
            />
          </div>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="BOM管理" name="bom">
        <el-card shadow="never" class="search-card">
          <el-form :inline="true" :model="bomSearch" class="search-form">
            <el-form-item label="BOM编码">
              <el-input v-model="bomSearch.bom_code" placeholder="请输入编码" clearable />
            </el-form-item>
            <el-form-item label="产品编码">
              <el-input v-model="bomSearch.product_code" placeholder="请输入产品编码" clearable />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Search" @click="fetchBomList">搜索</el-button>
              <el-button :icon="Refresh" @click="resetBomSearch">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
        <el-card shadow="never" class="table-card">
          <template #header>
            <div class="card-header">
              <span>BOM列表</span>
              <el-button type="primary" :icon="Plus">新增BOM</el-button>
            </div>
          </template>
          <el-table v-loading="bomLoading" :data="bomList" border stripe>
            <el-table-column prop="id" label="ID" width="80" align="center" />
            <el-table-column prop="bom_code" label="BOM编码" min-width="120" />
            <el-table-column prop="product_code" label="产品编码" min-width="120" />
            <el-table-column prop="level" label="层级" width="80" align="center" />
            <el-table-column prop="quantity" label="数量" width="100" align="center" />
            <el-table-column prop="created_at" label="创建时间" width="180" />
          </el-table>
          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="bomPagination.page"
              v-model:page-size="bomPagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="bomPagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="fetchBomList"
              @current-change="fetchBomList"
            />
          </div>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="工作中心" name="workcenter">
        <el-card shadow="never" class="table-card">
          <template #header><span>工作中心列表</span></template>
          <el-empty description="工作中心数据" />
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="工序管理" name="process">
        <el-card shadow="never" class="table-card">
          <template #header><span>工序列表</span></template>
          <el-empty description="工序数据" />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="materialDialogVisible" :title="isEditMaterial ? '编辑物料' : '新增物料'" width="600px" @close="resetMaterialForm">
      <el-form ref="materialFormRef" :model="materialForm" :rules="materialRules" label-width="100px">
        <el-form-item label="物料编码" prop="material_code">
          <el-input v-model="materialForm.material_code" placeholder="请输入物料编码" />
        </el-form-item>
        <el-form-item label="物料名称" prop="name">
          <el-input v-model="materialForm.name" placeholder="请输入物料名称" />
        </el-form-item>
        <el-form-item label="规格" prop="specification">
          <el-input v-model="materialForm.specification" placeholder="请输入规格" />
        </el-form-item>
        <el-form-item label="单位" prop="unit">
          <el-input v-model="materialForm.unit" placeholder="请输入单位" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="materialForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="materialDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="materialSubmitLoading" @click="handleSaveMaterial">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Plus, Edit } from '@element-plus/icons-vue'
import { getMaterialList, getBomList, createMaterial, updateMaterial } from '@/api/mes'

const activeTab = ref('material')

const materialLoading = ref(false)
const materialList = ref([])
const materialSearch = reactive({ material_code: '', name: '' })
const materialPagination = reactive({ page: 1, pageSize: 10, total: 0 })

const bomLoading = ref(false)
const bomList = ref([])
const bomSearch = reactive({ bom_code: '', product_code: '' })
const bomPagination = reactive({ page: 1, pageSize: 10, total: 0 })

// 物料对话框相关
const materialDialogVisible = ref(false)
const isEditMaterial = ref(false)
const materialSubmitLoading = ref(false)
const materialFormRef = ref(null)
const materialForm = reactive({
  id: null,
  material_code: '',
  name: '',
  specification: '',
  unit: '',
  is_active: true
})
const materialRules = {
  material_code: [
    { required: true, message: '请输入物料编码', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入物料名称', trigger: 'blur' }
  ]
}

const fetchMaterialList = async () => {
  materialLoading.value = true
  try {
    const res = await getMaterialList({
      page: materialPagination.page,
      page_size: materialPagination.pageSize,
      ...materialSearch
    })
    materialList.value = res.items || []
    materialPagination.total = res.total || 0
  } catch (e) { console.error('获取物料列表失败:', e) }
  finally { materialLoading.value = false }
}

const resetMaterialSearch = () => {
  materialSearch.material_code = ''
  materialSearch.name = ''
  materialPagination.page = 1
  fetchMaterialList()
}

const fetchBomList = async () => {
  bomLoading.value = true
  try {
    const res = await getBomList({
      page: bomPagination.page,
      page_size: bomPagination.pageSize,
      ...bomSearch
    })
    bomList.value = res.data.items || []
    bomPagination.total = res.data.total || 0
  } catch (e) { console.error('获取BOM列表失败:', e) }
  finally { bomLoading.value = false }
}

const resetBomSearch = () => {
  bomSearch.bom_code = ''
  bomSearch.product_code = ''
  bomPagination.page = 1
  fetchBomList()
}

const handleAddMaterial = () => {
  isEditMaterial.value = false
  materialForm.id = null
  materialForm.material_code = ''
  materialForm.name = ''
  materialForm.specification = ''
  materialForm.unit = ''
  materialForm.is_active = true
  materialDialogVisible.value = true
}

const handleEditMaterial = (row) => {
  isEditMaterial.value = true
  materialForm.id = row.id
  materialForm.material_code = row.material_code
  materialForm.name = row.name
  materialForm.specification = row.specification || ''
  materialForm.unit = row.unit || ''
  materialForm.is_active = row.is_active
  materialDialogVisible.value = true
}

const handleSaveMaterial = async () => {
  await materialFormRef.value.validate()
  materialSubmitLoading.value = true
  try {
    if (isEditMaterial.value) {
      await updateMaterial(materialForm.id, materialForm)
      ElMessage.success('更新成功')
    } else {
      await createMaterial(materialForm)
      ElMessage.success('创建成功')
    }
    materialDialogVisible.value = false
    fetchMaterialList()
  } catch (e) {
    console.error('提交失败:', e)
  } finally {
    materialSubmitLoading.value = false
  }
}

const resetMaterialForm = () => {
  materialFormRef.value?.resetFields()
}

onMounted(() => {
  fetchMaterialList()
})
</script>

<style lang="scss" scoped>
.mes-base {
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
