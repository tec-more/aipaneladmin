<template>
  <!-- 通用工作流节点：端口按注册表/节点声明生成；错误角标由校验态驱动（C9） -->
  <div
    class="wf-node"
    :class="[
      { 'is-error': hasError, 'is-selected': selected, 'is-running-state': !!runStatus },
      `node-${nodeType}`,
      runStatus ? `run-${runStatus}` : ''
    ]"
  >
    <div class="wf-node-header">
      <el-icon class="wf-node-icon"><component :is="iconComponent" /></el-icon>
      <span class="wf-node-label">{{ data.label || meta?.label }}</span>
      <span v-if="runStatus" class="wf-run-flag" :class="`flag-${runStatus}`">{{ runStatusText }}</span>
      <span v-if="hasError" class="wf-node-badge" title="存在校验错误" />
    </div>
    <div v-if="inputPorts.length || outputPorts.length" class="wf-node-ports">
      <div class="wf-node-ports-col">
        <div v-for="p in inputPorts" :key="`in-${p.name}`" class="wf-port">
          <Handle
            :id="p.name"
            type="target"
            :position="Position.Left"
            class="wf-handle"
          />
          <span class="wf-port-name">{{ p.name }}<i v-if="p.required" class="wf-port-required">*</i></span>
        </div>
      </div>
      <div class="wf-node-ports-col is-right">
        <div v-for="p in outputPorts" :key="`out-${p.name}`" class="wf-port is-out">
          <span class="wf-port-name">{{ p.name }}</span>
          <Handle
            :id="p.name"
            type="source"
            :position="Position.Right"
            class="wf-handle"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import * as Icons from '@element-plus/icons-vue'
import { getNodeMeta } from '@validator'
import { useCanvasStore } from '@/stores/canvas'
import { useExecutionStore } from '@/stores/execution'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, required: true },
  selected: { type: Boolean, default: false }
})

const canvasStore = useCanvasStore()
const executionStore = useExecutionStore()

const nodeType = computed(() => props.data?.nodeType || 'llm')
const meta = computed(() => getNodeMeta(nodeType.value))
const iconComponent = computed(() => Icons[meta.value?.icon] || Icons.Box)

const hasError = computed(() => canvasStore.errorNodeIds.has(props.id))

// T12 运行态着色：读 execution store 归约结果（seq 驱动，组件不消费事件流）
const RUN_TEXT = { running: '运行', completed: '完成', failed: '失败', paused: '待审批' }
const runStatus = computed(() => executionStore.nodeState[props.id]?.status || '')
const runStatusText = computed(() => RUN_TEXT[runStatus.value] || '')

// 端口声明：节点 data 声明优先，注册表默认兜底（与 resolvePortType 同序）
const inputPorts = computed(() => {
  if (Array.isArray(props.data?.inputs) && props.data.inputs.length) return props.data.inputs
  return meta.value?.inputs || []
})
const outputPorts = computed(() => {
  if (Array.isArray(props.data?.outputs) && props.data.outputs.length) return props.data.outputs
  return meta.value?.outputs || []
})
</script>

<style scoped lang="scss">
.wf-node {
  min-width: 168px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  font-size: 12px;
  transition: border-color 0.15s, box-shadow 0.15s;

  &.is-selected {
    border-color: var(--el-color-primary);
    box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.25);
  }
  &.is-error {
    border-color: var(--el-color-danger);
  }
}

.wf-node-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px solid #ebeef5;
  font-weight: 600;
  color: #303133;
}

.wf-node-icon {
  color: var(--el-color-primary);
  font-size: 14px;
}

.wf-node-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wf-node-badge {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--el-color-danger);
  flex-shrink: 0;
}

.wf-node-ports {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  gap: 8px;
}

.wf-node-ports-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.wf-port {
  position: relative;
  display: flex;
  align-items: center;
  height: 20px;
  padding: 0 10px;

  &.is-out {
    justify-content: flex-end;
  }
}

.wf-port-name {
  color: #909399;
  font-size: 11px;
  white-space: nowrap;
}

.wf-port-required {
  color: var(--el-color-danger);
  font-style: normal;
}

:deep(.wf-handle) {
  width: 8px;
  height: 8px;
  background: #fff;
  border: 2px solid var(--el-color-primary);
}

.node-start .wf-node-icon { color: var(--el-color-success); }
.node-end .wf-node-icon { color: var(--el-color-danger); }

/* ===== T12 运行态着色（seq 驱动，四色） ===== */
.wf-node.is-running-state { border-width: 2px; }
.wf-node.run-running { border-color: var(--el-color-primary); box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.2); }
.wf-node.run-completed { border-color: var(--el-color-success); }
.wf-node.run-failed { border-color: var(--el-color-danger); }
.wf-node.run-paused { border-color: var(--el-color-warning); }

.wf-run-flag {
  flex-shrink: 0;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
  line-height: 1.4;
}
.flag-running { background: rgba(64, 158, 255, 0.15); color: var(--el-color-primary); }
.flag-completed { background: rgba(103, 194, 58, 0.15); color: var(--el-color-success); }
.flag-failed { background: rgba(245, 108, 108, 0.15); color: var(--el-color-danger); }
.flag-paused { background: rgba(230, 162, 60, 0.15); color: var(--el-color-warning); }
</style>
