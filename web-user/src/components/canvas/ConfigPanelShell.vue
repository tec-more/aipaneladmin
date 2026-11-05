<template>
  <!-- 右侧配置壳（C5）：T8 仅 label 编辑 + 端口只读 + config JSON 预览；详细表单 T10 扩展 -->
  <el-drawer
    :model-value="!!node"
    :with-header="false"
    :modal="false"
    :size="360"
    direction="rtl"
    modal-class="config-panel-overlay"
    class="config-panel"
    @close="canvasStore.clearSelection()"
  >
    <div v-if="node" class="panel-body">
      <div class="panel-header">
        <el-icon class="panel-icon"><component :is="iconComponent" /></el-icon>
        <span class="panel-title">{{ meta?.label || node.data?.nodeType }}</span>
        <el-tag size="small" effect="plain">{{ node.data?.nodeType }}</el-tag>
      </div>

      <el-form label-position="top" size="default">
        <el-form-item label="节点名称">
          <el-input
            :model-value="node.data?.label"
            maxlength="50"
            show-word-limit
            placeholder="请输入节点名称"
            @update:model-value="onLabelChange"
          />
        </el-form-item>
      </el-form>

      <el-divider content-position="left">端口</el-divider>
      <div class="port-section">
        <div class="port-group">
          <div class="port-group-title">输入</div>
          <el-empty v-if="!inputPorts.length" description="无输入端口" :image-size="40" />
          <div v-for="p in inputPorts" :key="`in-${p.name}`" class="port-row">
            <span class="port-name">{{ p.name }}<i v-if="p.required" class="port-required">*</i></span>
            <el-tag size="small" type="info" effect="plain">{{ p.type }}</el-tag>
          </div>
        </div>
        <div class="port-group">
          <div class="port-group-title">输出</div>
          <el-empty v-if="!outputPorts.length" description="无输出端口" :image-size="40" />
          <div v-for="p in outputPorts" :key="`out-${p.name}`" class="port-row">
            <span class="port-name">{{ p.name }}</span>
            <el-tag size="small" type="success" effect="plain">{{ p.type }}</el-tag>
          </div>
        </div>
      </div>

      <el-divider content-position="left">节点配置</el-divider>
      <!-- T10：registry 有 fields 声明 → 表单；无（降级/未知节点）→ 只读兜底（K10） -->
      <NodeConfigForm
        v-if="meta && (meta.fields || []).length"
        :key="node.id"
        :node="node"
        @update-config="onConfigUpdate"
      />
      <ReadonlyConfigView v-else :config="node.data?.config || {}" />
    </div>
  </el-drawer>
</template>

<script setup>
import { computed } from 'vue'
import * as Icons from '@element-plus/icons-vue'
import { getNodeMeta } from '@validator'
import { useCanvasStore } from '@/stores/canvas'
import NodeConfigForm from './forms/NodeConfigForm.vue'
import ReadonlyConfigView from './forms/ReadonlyConfigView.vue'

const canvasStore = useCanvasStore()

const node = computed(() =>
  canvasStore.nodes.find((n) => n.id === canvasStore.selectedNodeId) || null
)
const meta = computed(() => (node.value ? getNodeMeta(node.value.data?.nodeType) : null))
const iconComponent = computed(() => Icons[meta.value?.icon] || Icons.Box)

const inputPorts = computed(() => {
  if (!node.value) return []
  const declared = node.value.data?.inputs
  return Array.isArray(declared) && declared.length ? declared : (meta.value?.inputs || [])
})
const outputPorts = computed(() => {
  if (!node.value) return []
  const declared = node.value.data?.outputs
  return Array.isArray(declared) && declared.length ? declared : (meta.value?.outputs || [])
})

/** config 写回（NodeConfigForm 防抖后提交，经 store 入历史栈与自动保存链） */
function onConfigUpdate(config) {
  if (node.value) canvasStore.updateNodeConfig(node.value.id, config)
}

/** label 改名（失焦提交，经 store 入历史栈） */
let pending = null
function onLabelChange(val) {
  pending = val
  clearTimeout(onLabelChange._t)
  onLabelChange._t = setTimeout(() => {
    if (node.value && pending !== node.value.data?.label) {
      canvasStore.updateNodeMeta(node.value.id, { label: pending })
    }
  }, 400)
}
</script>

<style scoped lang="scss">
.panel-body {
  padding: 4px 4px 24px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.panel-icon {
  font-size: 18px;
  color: var(--el-color-primary);
}

.panel-title {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.port-group {
  margin-bottom: 12px;
}

.port-group-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.port-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  margin-bottom: 4px;
  font-size: 12px;
}

.port-required {
  color: var(--el-color-danger);
  font-style: normal;
}

.config-tip {
  margin-bottom: 8px;
}

.config-json {
  margin: 0;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #606266;
  max-height: 260px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>

<style lang="scss">
/* el-drawer modal=false 时 ElOverlay 仍渲染全屏透明 div，会拦截画布点击且自身无 click
   处理（点击关不掉、选不了其它节点）。让遮罩穿透、面板自身保留交互；关闭走
   pane-click -> clearSelection -> model-value 变 false 的链路。 */
.config-panel-overlay {
  pointer-events: none;

  .el-drawer {
    pointer-events: auto;
  }
}
</style>
