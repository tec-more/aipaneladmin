<template>
  <!-- 试跑控制条：试跑/取消/状态徽标/Trace 开关/HITL 审批入口（T12） -->
  <div class="run-panel">
    <el-button
      v-if="!exec.running"
      type="success"
      :icon="VideoPlay"
      size="small"
      :disabled="canvasStore.hasBlockingIssues"
      @click="$emit('run')"
    >试跑</el-button>
    <template v-else>
      <el-tag :type="statusTag" effect="dark" size="small" class="run-status">
        <el-icon class="is-loading" style="margin-right:4px"><Loading /></el-icon>{{ statusText }}
      </el-tag>
      <el-button type="danger" :icon="CircleClose" size="small" @click="onCancel">取消</el-button>
    </template>

    <el-button
      v-if="exec.status === 'paused'"
      type="warning"
      size="small"
      @click="$emit('hitl')"
    >审批处理</el-button>

    <el-tag v-if="exec.isTerminal" :type="terminalTag" size="small" effect="plain">{{ terminalText }}</el-tag>
    <el-tooltip v-if="exec.totalTokens != null" content="本次消耗 tokens" placement="bottom">
      <el-tag size="small" effect="plain" type="info">{{ exec.totalTokens }} tokens</el-tag>
    </el-tooltip>
    <span v-if="exec.notice" class="run-notice">{{ exec.notice }}</span>

    <el-button
      text
      size="small"
      :icon="Tickets"
      style="margin-left:auto"
      @click="$emit('toggle-trace')"
    >Trace</el-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessageBox } from 'element-plus'
import { VideoPlay, CircleClose, Loading, Tickets } from '@element-plus/icons-vue'
import { useExecutionStore } from '@/stores/execution'
import { useCanvasStore } from '@/stores/canvas'

const emit = defineEmits(['run', 'toggle-trace', 'hitl'])
const exec = useExecutionStore()
const canvasStore = useCanvasStore()

const STATUS_TEXT = {
  connecting: '连接中', streaming: '运行中', paused: '待审批', replaying: '回放补齐'
}
const statusText = computed(() => STATUS_TEXT[exec.status] || '')
const statusTag = computed(() => (exec.status === 'paused' ? 'warning' : 'primary'))

const TERMINAL_TEXT = { completed: '执行完成', failed: '执行失败', cancelled: '已取消' }
const terminalText = computed(() => TERMINAL_TEXT[exec.status] || '')
const terminalTag = computed(() => ({ completed: 'success', failed: 'danger', cancelled: 'info' }[exec.status] || 'info'))

function onCancel() {
  ElMessageBox.confirm('确定取消本次试跑？', '取消确认', { type: 'warning' })
    .then(() => exec.cancel())
    .catch(() => {})
}
</script>

<style scoped lang="scss">
.run-panel {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}
.run-notice { font-size: 12px; color: var(--el-color-warning); }
</style>
