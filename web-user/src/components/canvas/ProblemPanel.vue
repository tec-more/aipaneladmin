<template>
  <!-- 底部问题面板（C9）：双源 issue（本地 + 服务端）渲染，点击定位节点 -->
  <div class="problem-panel" :class="{ 'is-open': open }">
    <div class="panel-bar" @click="open = !open">
      <span class="bar-title">
        问题
        <el-badge v-if="errorCount" :value="errorCount" type="danger" class="bar-badge" />
        <el-badge v-if="warningCount" :value="warningCount" type="warning" class="bar-badge" />
        <span v-if="!errorCount && !warningCount" class="bar-ok">无</span>
      </span>
      <el-icon class="bar-arrow" :class="{ 'is-open': open }"><ArrowUp /></el-icon>
    </div>
    <div v-show="open" class="panel-list">
      <el-empty v-if="!allIssues.length" description="暂无问题" :image-size="48" />
      <div
        v-for="(it, idx) in allIssues"
        :key="idx"
        class="issue-row"
        :class="`is-${it.level}`"
        @click="onLocate(it)"
      >
        <el-icon class="issue-icon">
          <CircleCloseFilled v-if="it.level === 'error'" />
          <WarningFilled v-else />
        </el-icon>
        <span class="issue-code">{{ it.code }}</span>
        <span class="issue-message" :title="it.message">{{ it.message }}</span>
        <el-tag v-if="it._source === 'server'" size="small" effect="plain" class="issue-source">服务端</el-tag>
        <el-button
          v-if="it.node_id"
          size="small"
          text
          type="primary"
          @click.stop="onLocate(it)"
        >定位</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ArrowUp, CircleCloseFilled, WarningFilled } from '@element-plus/icons-vue'
import { useCanvasStore } from '@/stores/canvas'

const emit = defineEmits(['locate'])
const canvasStore = useCanvasStore()
const open = ref(false)

/** 双源合并：标注来源便于区分（结构同构零转换） */
const allIssues = computed(() => [
  ...canvasStore.localIssues.map((i) => ({ ...i, _source: 'local' })),
  ...canvasStore.serverIssues.map((i) => ({ ...i, _source: 'server' }))
])

const errorCount = computed(() => allIssues.value.filter((i) => i.level === 'error').length)
const warningCount = computed(() => allIssues.value.filter((i) => i.level === 'warning').length)

function onLocate(issue) {
  if (!issue.node_id) return
  canvasStore.selectNode(issue.node_id)
  emit('locate', issue.node_id)
}
</script>

<style scoped lang="scss">
.problem-panel {
  flex-shrink: 0;
  background: #fff;
  border-top: 1px solid #e4e7ed;
}

.panel-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  cursor: pointer;
  user-select: none;

  &:hover {
    background: #f5f7fa;
  }
}

.bar-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.bar-ok {
  font-weight: 400;
  color: #909399;
}

.bar-arrow {
  transition: transform 0.2s;
  color: #909399;

  &.is-open {
    transform: rotate(180deg);
  }
}

.panel-list {
  max-height: 200px;
  overflow-y: auto;
  border-top: 1px solid #ebeef5;
}

.issue-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  font-size: 12px;
  cursor: pointer;

  &:hover {
    background: #f5f7fa;
  }

  &.is-error .issue-icon {
    color: var(--el-color-danger);
  }

  &.is-warning .issue-icon {
    color: var(--el-color-warning);
  }
}

.issue-code {
  color: #909399;
  flex-shrink: 0;
}

.issue-message {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #606266;
}

.issue-source {
  flex-shrink: 0;
}
</style>
