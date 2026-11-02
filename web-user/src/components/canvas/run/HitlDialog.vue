<template>
  <!-- HITL 审批框：approve/reject + comment（cus P0 仅自审，T12） -->
  <el-dialog v-model="visible" title="人工审批" width="460px" :close-on-click-modal="false">
    <el-alert type="warning" :closable="false" style="margin-bottom:12px">
      工作流在节点「{{ nodeLabel }}」等待人工处理
    </el-alert>
    <el-form label-position="top">
      <el-form-item label="处理意见（可选）">
        <el-input v-model="comment" type="textarea" :rows="3" placeholder="审批意见" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button type="danger" :loading="acting" @click="onAct(false)">拒绝</el-button>
      <el-button type="success" :loading="acting" @click="onAct(true)">通过</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useExecutionStore } from '@/stores/execution'
import { useCanvasStore } from '@/stores/canvas'

const exec = useExecutionStore()
const canvasStore = useCanvasStore()

const visible = ref(false)
const comment = ref('')
const acting = ref(false)

const nodeLabel = computed(() => {
  const nid = exec.hitl?.node_id
  return nid ? (canvasStore.nodes.find((n) => n.id === nid)?.data?.label || nid) : ''
})

function open() { comment.value = ''; visible.value = true }

async function onAct(approved) {
  acting.value = true
  try {
    await exec.resume(approved, comment.value || undefined)
    visible.value = false
  } finally {
    acting.value = false
  }
}

defineExpose({ open })
</script>
