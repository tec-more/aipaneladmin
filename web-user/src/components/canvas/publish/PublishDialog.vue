<template>
  <!-- 发布确认框（T13）：版本描述 + 校验前置提示 + 幂等键（同次重试复用） -->
  <el-dialog v-model="visible" title="发布工作流" width="480px" :close-on-click-modal="false">
    <el-alert type="info" :closable="false" style="margin-bottom:12px">
      发布将基于当前草稿生成一个不可变版本（版本号自增）。发布前服务端会全量校验，存在阻断错误将失败。
    </el-alert>
    <el-form label-position="top">
      <el-form-item label="版本描述（可选）">
        <el-input v-model="description" type="textarea" :rows="2" maxlength="200" show-word-limit placeholder="本次发布说明" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="publishing" @click="onPublish">确认发布</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { publishWorkflow } from '@/api/workflow'

const emit = defineEmits(['published', 'blocked'])

const visible = ref(false)
const publishing = ref(false)
const description = ref('')
let workflowId = null
// 幂等键：同一确认框会话内复用，防止网络重试/双击产生重复版本（04-F1）
let idemKey = ''

function open(id) {
  workflowId = id
  description.value = ''
  idemKey = (crypto.randomUUID && crypto.randomUUID()) || `${Date.now()}-${Math.random()}`
  visible.value = true
}

async function onPublish() {
  if (publishing.value) return
  publishing.value = true
  try {
    const res = await publishWorkflow(workflowId, idemKey, description.value)
    const data = res?.data ?? res
    ElMessage.success(`发布成功，版本 v${data?.version_no}`)
    visible.value = false
    emit('published', data)
  } catch (err) {
    const code = err?.data?.error?.code
    if (code === 42200) {
      // 全量校验阻断：透传问题面板（编辑器消费）
      emit('blocked', err?.data?.error?.details?.issues || [])
      ElMessage.error('发布被阻断：存在校验错误，请查看问题面板')
      visible.value = false
    } else if (code === 40901) {
      ElMessage.error('草稿已变化，请刷新后重试发布')
      visible.value = false
    }
    // 其余错误拦截器已提示
  } finally {
    publishing.value = false
  }
}

defineExpose({ open })
</script>
