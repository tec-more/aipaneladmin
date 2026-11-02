<template>
  <!-- Trace 回放抽屉：事件时间线（按 seq 升序）+ token 聚合 + usage（T12） -->
  <el-drawer
    :model-value="modelValue"
    title="执行 Trace"
    size="440px"
    :with-header="true"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="trace-body">
      <el-empty v-if="!events.length" description="暂无执行事件" :image-size="80" />
      <div v-else ref="listRef" class="trace-list">
        <div
          v-for="ev in events"
          :key="ev.seq + '-' + ev.event_type + '-' + (ev.node_id || '')"
          class="trace-item"
          :class="`t-${category(ev.event_type)}`"
        >
          <div class="trace-line">
            <span class="trace-seq">#{{ ev.seq }}</span>
            <el-icon class="trace-icon"><component :is="icon(ev.event_type)" /></el-icon>
            <span class="trace-name">{{ label(ev.event_type) }}</span>
            <span v-if="ev.node_id" class="trace-node">{{ nodeLabel(ev.node_id) }}</span>
            <span v-if="ev.payload?.ms != null" class="trace-ms">{{ ev.payload.ms }}ms</span>
          </div>
          <!-- token 流式聚合（同 node 追加，非逐条 DOM，R-A） -->
          <div v-if="ev.event_type === 'node_started' && tokenText(ev.node_id)" class="trace-token">
            {{ tokenText(ev.node_id) }}
          </div>
          <div v-if="ev.event_type === 'node_failed' && ev.payload?.error" class="trace-err">
            {{ ev.payload.error.message || ev.payload.error.code }}
          </div>
          <div v-if="ev.event_type === 'run_failed' && ev.payload?.error" class="trace-err">
            {{ ev.payload.error.message || ev.payload.error.code }}
          </div>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import * as Icons from '@element-plus/icons-vue'
import { useExecutionStore } from '@/stores/execution'
import { useCanvasStore } from '@/stores/canvas'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
defineEmits(['update:modelValue'])

const exec = useExecutionStore()
const canvasStore = useCanvasStore()
const listRef = ref(null)

// 过滤 token 帧（聚合展示，避免逐帧刷屏），其余事件全量按 seq 升序
const events = computed(() => exec.events.filter((e) => e.event_type !== 'token'))

const ICON_MAP = {
  run_started: 'VideoPlay', node_started: 'Right', node_completed: 'CircleCheck',
  node_failed: 'CircleClose', run_paused: 'AlarmClock', run_completed: 'SuccessFilled', run_failed: 'WarningFilled'
}
const LABEL_MAP = {
  run_started: '开始执行', node_started: '节点开始', node_completed: '节点完成',
  node_failed: '节点失败', run_paused: '等待审批', run_completed: '执行完成', run_failed: '执行失败'
}
const icon = (t) => Icons[ICON_MAP[t]] || Icons.More
const label = (t) => LABEL_MAP[t] || t
const category = (t) => (t.includes('failed') ? 'err' : t.includes('completed') ? 'ok' : t.includes('paused') ? 'warn' : 'info')

const nodeLabel = (nid) => canvasStore.nodes.find((n) => n.id === nid)?.data?.label || nid
const tokenText = (nid) => (nid ? exec.tokenBuffer[nid] || '' : '')

// 新事件自动滚底
watch(() => exec.events.length, async () => {
  await nextTick()
  if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
})
</script>

<style scoped lang="scss">
.trace-body { height: 100%; }
.trace-list { height: 100%; overflow-y: auto; padding-right: 4px; }
.trace-item { padding: 6px 4px; border-bottom: 1px solid #f0f2f5; }
.trace-line { display: flex; align-items: center; gap: 6px; font-size: 12px; }
.trace-seq { color: #c0c4cc; font-family: monospace; min-width: 30px; }
.trace-icon { font-size: 14px; }
.t-ok .trace-icon { color: var(--el-color-success); }
.t-err .trace-icon { color: var(--el-color-danger); }
.t-warn .trace-icon { color: var(--el-color-warning); }
.t-info .trace-icon { color: var(--el-color-primary); }
.trace-name { color: #303133; font-weight: 600; }
.trace-node { color: #909399; }
.trace-ms { margin-left: auto; color: #c0c4cc; font-size: 11px; }
.trace-token {
  margin: 4px 0 0 30px; padding: 6px 8px; background: #f5f7fa; border-radius: 4px;
  font-size: 12px; color: #606266; white-space: pre-wrap; word-break: break-word;
}
.trace-err { margin: 4px 0 0 30px; font-size: 12px; color: var(--el-color-danger); }
</style>
