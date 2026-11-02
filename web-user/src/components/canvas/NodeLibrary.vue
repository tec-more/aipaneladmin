<template>
  <!-- 左侧节点库：按分类分组；open 可拖，gray/disabled 置灰 + 原因（C1） -->
  <!-- T11：node_type 授权驱动动态置灰（hitl/sub_agent/tool 未授权保持 gray） -->
  <aside class="node-library">
    <div class="library-title">节点库</div>
    <el-scrollbar class="library-scroll">
      <div v-for="cat in categories" :key="cat" class="library-group">
        <div class="group-name">{{ cat }}</div>
        <div
          v-for="item in grouped[cat]"
          :key="item.type"
          class="node-item"
          :class="{ 'is-disabled': !isOpen(item) }"
          :draggable="isOpen(item)"
          @dragstart="onDragStart($event, item)"
        >
          <el-icon class="node-item-icon"><component :is="iconOf(item.icon)" /></el-icon>
          <span class="node-item-label">{{ item.label }}</span>
          <el-tooltip
            v-if="!isOpen(item)"
            :content="disabledReason(item)"
            placement="right"
          >
            <el-icon class="node-item-lock"><Lock /></el-icon>
          </el-tooltip>
        </div>
      </div>
    </el-scrollbar>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { Lock } from '@element-plus/icons-vue'
import * as Icons from '@element-plus/icons-vue'
import { NODE_REGISTRY, NODE_CATEGORIES } from '@validator'
import { useResourceStore } from '@/stores/resource'

const categories = NODE_CATEGORIES
const resourceStore = useResourceStore()

const grouped = computed(() => {
  const map = {}
  for (const cat of categories) map[cat] = []
  for (const meta of Object.values(NODE_REGISTRY)) {
    if (map[meta.category]) map[meta.category].push(meta)
  }
  return map
})

// node_type 授权集（T11 Q3：resource_type='node_type'，resource_id=类型编码）
const grantedTypes = computed(() => resourceStore.grantedNodeTypes)

/**
 * 开放判定（T11）：
 * - open（白名单基础节点）：恒可用
 * - gray（受限节点 hitl/sub_agent/tool）：需 node_type 授权，未授权保持置灰
 * - disabled（http/vector/code）：恒不可用
 */
function isOpen(item) {
  if (item.availability === 'open') return true
  if (item.availability === 'disabled') return false
  // gray：查授权
  return grantedTypes.value.has(item.type)
}

function disabledReason(item) {
  if (item.availability === 'disabled') return item.disabledReason || '未开放'
  // gray 未授权
  return `需管理员授权「${item.label}」节点类型后可用`
}

function iconOf(name) {
  return Icons[name] || Icons.Box
}

/** 拖拽源：dataTransfer 携带节点类型（画布 drop 消费，C2） */
function onDragStart(event, item) {
  if (!isOpen(item)) return
  event.dataTransfer.setData('application/wf-node-type', item.type)
  event.dataTransfer.effectAllowed = 'move'
}
</script>

<style scoped lang="scss">
.node-library {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #e4e7ed;
}

.library-title {
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
}

.library-scroll {
  flex: 1;
}

.library-group {
  padding: 8px 12px;
}

.group-name {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  margin-bottom: 4px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  cursor: grab;
  font-size: 13px;
  color: #303133;
  transition: border-color 0.15s, box-shadow 0.15s;

  &:hover:not(.is-disabled) {
    border-color: var(--el-color-primary);
    box-shadow: 0 1px 4px rgba(64, 158, 255, 0.2);
  }

  &.is-disabled {
    cursor: not-allowed;
    color: #c0c4cc;
    background: #fafafa;
  }
}

.node-item-icon {
  color: var(--el-color-primary);
}

.node-item.is-disabled .node-item-icon {
  color: #c0c4cc;
}

.node-item-label {
  flex: 1;
}

.node-item-lock {
  font-size: 12px;
}
</style>
