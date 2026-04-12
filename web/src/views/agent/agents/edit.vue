<template>
  <div class="agent-edit">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-button @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <span>{{ isEdit ? '编辑智能体' : '创建智能体' }}</span>
          <div class="header-right">
            <el-button type="primary" @click="handleSubmit" :loading="saving">
              <el-icon><Check /></el-icon>
              保存
            </el-button>
          </div>
        </div>
      </template>

      <el-form :model="formData" :rules="rules" ref="formRef" label-width="120px" style="max-width: 800px;">
        <el-form-item label="智能体名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入智能体名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="formData.description" type="textarea" :rows="3" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="formData.status" placeholder="请选择状态" style="width: 100%">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="记忆容量" prop="memory_capacity">
          <el-input-number v-model="formData.memory_capacity" :min="1" :max="10000" />
          <span style="margin-left: 10px; color: #909399;">条</span>
        </el-form-item>
        <el-form-item label="系统提示词">
          <el-input v-model="formData.system_prompt" type="textarea" :rows="6" placeholder="请输入系统提示词" />
        </el-form-item>
        <el-form-item label="配置">
          <el-input v-model="configJson" type="textarea" :rows="6" placeholder="JSON格式配置" />
        </el-form-item>
        <el-form-item label="关联技能">
          <el-select v-model="formData.skill_ids" multiple placeholder="请选择技能" style="width: 100%">
            <el-option v-for="skill in allSkills" :key="skill.id" :label="skill.name" :value="skill.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联工作流">
          <el-select v-model="formData.workflow_ids" multiple placeholder="请选择工作流" style="width: 100%">
            <el-option v-for="workflow in allWorkflows" :key="workflow.id" :label="workflow.name" :value="workflow.id" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAgent, createAgent, updateAgent, getAgentSkills, setAgentSkills, getSkills, getWorkflows } from '@/api/agent'

const route = useRoute()
const router = useRouter()
const formRef = ref(null)
const saving = ref(false)
const allSkills = ref([])
const allWorkflows = ref([])

const agentId = route.params.id
const isEdit = computed(() => !!agentId)

const formData = reactive({
  name: '',
  description: '',
  status: 'active',
  memory_capacity: 100,
  system_prompt: '',
  config: {},
  skill_ids: [],
  workflow_ids: []
})

const configJson = computed({
  get: () => {
    try {
      return JSON.stringify(formData.config, null, 2)
    } catch {
      return '{}'
    }
  },
  set: (val) => {
    try {
      formData.config = JSON.parse(val)
    } catch (e) {}
  }
})

const rules = {
  name: [{ required: true, message: '请输入智能体名称', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

const goBack = () => {
  router.push('/panel/agent/list')
}

const fetchAgent = async () => {
  if (!agentId) return
  try {
    const res = await getAgent(agentId)
    Object.assign(formData, {
      ...res.data,
      skill_ids: [],
      workflow_ids: []
    })
    const skillsRes = await getAgentSkills(agentId)
    formData.skill_ids = skillsRes.data || []
  } catch (error) {
    ElMessage.error('获取智能体信息失败')
    console.error(error)
  }
}

const fetchSkills = async () => {
  try {
    const res = await getSkills({ limit: 1000 })
    allSkills.value = res.data?.items || res.data || []
  } catch (error) {
    console.error(error)
  }
}

const fetchWorkflows = async () => {
  try {
    const res = await getWorkflows({ limit: 1000 })
    allWorkflows.value = res.data?.items || res.data || []
  } catch (error) {
    console.error(error)
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true
      try {
        const submitData = {
          name: formData.name,
          description: formData.description,
          status: formData.status,
          memory_capacity: formData.memory_capacity,
          system_prompt: formData.system_prompt,
          config: formData.config
        }
        
        if (isEdit.value) {
          await updateAgent(agentId, submitData)
          await setAgentSkills(agentId, formData.skill_ids)
          ElMessage.success('更新成功')
        } else {
          const res = await createAgent(submitData)
          if (formData.skill_ids.length > 0) {
            await setAgentSkills(res.data.id, formData.skill_ids)
          }
          ElMessage.success('创建成功')
          router.push(`/panel/agent/edit/${res.data.id}`)
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

onMounted(() => {
  fetchSkills()
  fetchWorkflows()
  if (isEdit.value) {
    fetchAgent()
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
}
</style>
