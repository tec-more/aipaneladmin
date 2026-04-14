<template>
  <div class="skill-edit">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ isEdit ? '编辑技能' : '创建技能' }}</span>
          <div class="header-right">
            <el-button type="primary" @click="handleSubmit" :loading="saving">
              <el-icon><Check /></el-icon>
              <span v-if="isEdit">保存</span>
              <span v-else>创建</span>
            </el-button>
            <el-button 
              type="warning" 
              @click="publishSkill" 
              v-if="isEdit && formData.status !== 'active'"
            >
              <el-icon><Check /></el-icon>
              发布
            </el-button>
            <el-button type="success" @click="handleTest" v-if="isEdit" :loading="testing">
              <el-icon><VideoPlay /></el-icon>
              测试
            </el-button>
          </div>
        </div>
      </template>

      <el-form :model="formData" :rules="rules" ref="formRef" label-width="120px" style="max-width: 800px;">
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
          <el-select v-model="formData.status" placeholder="请选择状态" style="width: 100%">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="参数配置">
          <el-input v-model="parametersJson" type="textarea" :rows="6" placeholder="JSON格式参数配置" />
        </el-form-item>
        <el-form-item label="实现代码">
          <el-input v-model="formData.implementation" type="textarea" :rows="10" placeholder="技能实现代码（Python）" />
        </el-form-item>
        <el-form-item label="依赖包">
          <el-input v-model="formData.dependencies" type="textarea" :rows="3" placeholder="依赖包列表，每行一个" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog v-model="testDialogVisible" title="测试技能" width="600px">
      <el-form :model="testForm" label-width="100px">
        <el-form-item label="输入参数">
          <el-input v-model="testForm.input" type="textarea" :rows="4" placeholder="JSON格式输入参数" />
        </el-form-item>
        <el-form-item label="执行结果">
          <el-input v-model="testResult" type="textarea" :rows="6" readonly placeholder="执行结果" />
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
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Check, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getSkill, createSkill, updateSkill, executeSkill } from '@/api/agent'

const route = useRoute()
const router = useRouter()
const formRef = ref(null)
const saving = ref(false)
const testing = ref(false)
const testDialogVisible = ref(false)
const testLoading = ref(false)
const testForm = reactive({ input: '{}' })
const testResult = ref('')

const skillId = route.params.id
const isEdit = computed(() => !!skillId)

const formData = reactive({
  name: '',
  type: 'tool',
  description: '',
  status: 'active',
  parameters: {},
  implementation: '',
  dependencies: ''
})

const parametersJson = computed({
  get: () => {
    try {
      return JSON.stringify(formData.parameters, null, 2)
    } catch {
      return '{}'
    }
  },
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

const goBack = () => {
  router.push('/panel/agent/skills')
}

const fetchSkill = async () => {
  if (!skillId) return
  try {
    const res = await getSkill(skillId)
    Object.assign(formData, res.data)
  } catch (error) {
    ElMessage.error('获取技能信息失败')
    console.error(error)
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true
      try {
        if (isEdit.value) {
          await updateSkill(skillId, formData)
          ElMessage.success('更新成功')
        } else {
          const res = await createSkill(formData)
          ElMessage.success('创建成功')
          router.push(`/panel/agent/skills/edit/${res.data.id}`)
        }
      } catch (error) {
        ElMessage.error('保存失败')
        console.error(error)
      } finally {
        saving.value = false
      }
    }
  })
}

const handleTest = () => {
  testForm.input = JSON.stringify(formData.parameters, null, 2)
  testResult.value = ''
  testDialogVisible.value = true
}

const publishSkill = async () => {
  saving.value = true
  try {
    await updateSkill(skillId, {
      ...formData,
      status: 'active'
    })
    formData.status = 'active'
    ElMessage.success('发布成功')
  } catch (error) {
    ElMessage.error('发布失败')
    console.error(error)
  } finally {
    saving.value = false
  }
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
    const res = await executeSkill(skillId, input)
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
  if (isEdit.value) {
    fetchSkill()
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  gap: 16px;
}
.header-right {
  margin-left: auto;
  display: flex;
  gap: 10px;
}
</style>
