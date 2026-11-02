<template>
  <!-- VueFlow 宿主：渲染/拖拽/连线/框选/缩放（C2/C3/C4/C7/C8）；校验规则一律经 @validator -->
  <div class="workflow-canvas" @drop="onDrop" @dragover.prevent @keydown.delete.prevent="onDeleteKey" tabindex="0">
    <VueFlow
      v-model:nodes="canvasStore.nodes"
      v-model:edges="canvasStore.edges"
      :node-types="nodeTypes"
      :snap-to-grid="true"
      :snap-grid="[20, 20]"
      :min-zoom="0.2"
      :max-zoom="2"
      :default-viewport="{ zoom: 1 }"
      :delete-key-code="null"
      :nodes-draggable="!readonly"
      :nodes-connectable="!readonly"
      :edges-updatable="!readonly"
      fit-view-on-init
      @connect="onConnect"
      @node-click="onNodeClick"
      @edge-click="onEdgeClick"
      @pane-click="canvasStore.clearSelection()"
      @node-drag-stop="onNodeDragStop"
    >
      <Background :gap="20" pattern-color="#c0c4cc" />
      <Controls />
      <MiniMap pannable zoomable />
    </VueFlow>

    <!-- 顶部工具条：撤销/重做/整理布局/适应画布（C7/C8）；试跑只读时禁用编辑类操作 -->
    <div class="canvas-toolbar">
      <el-tooltip content="撤销（Ctrl+Z）" placement="bottom">
        <el-button :icon="RefreshLeft" :disabled="readonly || !canvasStore.canUndo" circle @click="canvasStore.undo()" />
      </el-tooltip>
      <el-tooltip content="重做（Ctrl+Y）" placement="bottom">
        <el-button :icon="RefreshRight" :disabled="readonly || !canvasStore.canRedo" circle @click="canvasStore.redo()" />
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip content="整理布局" placement="bottom">
        <el-button :icon="Grid" :disabled="readonly" circle @click="autoLayout" />
      </el-tooltip>
      <el-tooltip content="适应画布" placement="bottom">
        <el-button :icon="FullScreen" circle @click="fitView()" />
      </el-tooltip>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { ElMessage } from 'element-plus'
import { RefreshLeft, RefreshRight, Grid, FullScreen } from '@element-plus/icons-vue'
import { validateConnection } from '@validator'
import { useCanvasStore } from '@/stores/canvas'
import { createNodeByType, makeEdgeId } from '@/utils/graphSerializer'
import { nodeTypes } from './nodes/nodeTypes'

// T12：试跑中只读（禁拖拽/连线/删除，保留平移缩放查看）
const props = defineProps({ readonly: { type: Boolean, default: false } })
const canvasStore = useCanvasStore()
const { fitView, screenToFlowCoordinate, removeNodes, removeEdges } = useVueFlow()

/** 连线落图：先过连线期校验（C3/C4），通过才入图 */
function onConnect(conn) {
  const issue = validateConnection(canvasStore.collectGraph(), conn)
  if (issue) {
    ElMessage.error(`${issue.code} ${issue.message}`)
    return
  }
  canvasStore.applyConnect(conn, makeEdgeId(conn))
}

function onNodeClick({ node }) {
  canvasStore.selectNode(node.id)
}

function onEdgeClick({ edge }) {
  canvasStore.selectEdge(edge.id)
}

/** 拖拽过程不入历史，dragStop 一次性入栈（避免历史爆炸） */
function onNodeDragStop() {
  canvasStore.commitMove()
}

/** Delete 删除选中节点/边（禁用 VueFlow 默认删除键，改走 store 保证入历史栈） */
function onDeleteKey() {
  if (props.readonly) return
  if (canvasStore.selectedNodeId) {
    canvasStore.removeNode(canvasStore.selectedNodeId)
  } else if (canvasStore.selectedEdgeId) {
    canvasStore.removeEdge(canvasStore.selectedEdgeId)
  }
}

/** 节点库拖入创建（C2）：屏幕坐标 → 画布坐标（含缩放） */
function onDrop(event) {
  if (props.readonly) return
  const nodeType = event.dataTransfer?.getData('application/wf-node-type')
  if (!nodeType) return
  const position = screenToFlowCoordinate({ x: event.clientX, y: event.clientY })
  try {
    const seq = canvasStore.nodes.length + 1
    canvasStore.addNode(createNodeByType(nodeType, position, seq))
  } catch (e) {
    ElMessage.error(e.message || '节点创建失败')
  }
}

/** 简单分层布局：按 BFS 深度分列（T8 范围；复杂布局库经评审后再引入） */
function autoLayout() {
  const nodes = canvasStore.nodes
  if (!nodes.length) return
  const start = nodes.find((n) => n.data?.nodeType === 'start')
  const depth = new Map()
  const adj = new Map()
  for (const e of canvasStore.edges) {
    if (!adj.has(e.source)) adj.set(e.source, [])
    adj.get(e.source).push(e.target)
  }
  const queue = start ? [[start.id, 0]] : []
  while (queue.length) {
    const [id, d] = queue.shift()
    if (depth.has(id)) continue
    depth.set(id, d)
    for (const nxt of adj.get(id) || []) queue.push([nxt, d + 1])
  }
  canvasStore.snapshot()
  const colGap = 260
  const rowGap = 110
  const rowCount = new Map()
  nodes.forEach((n) => {
    const d = depth.get(n.id) ?? 0
    const row = rowCount.get(d) || 0
    rowCount.set(d, row + 1)
    n.position = { x: 80 + d * colGap, y: 60 + row * rowGap }
  })
  canvasStore._afterChange()
  fitView()
}

/** 快捷键：Ctrl+Z / Ctrl+Y（C7） */
function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && !e.shiftKey) {
    e.preventDefault()
    canvasStore.undo()
  } else if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'y' || (e.key.toLowerCase() === 'z' && e.shiftKey))) {
    e.preventDefault()
    canvasStore.redo()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  removeNodes([]) // 明确释放引用（防御性；store.reset 由 Editor 负责）
  removeEdges([])
})
</script>

<style scoped lang="scss">
.workflow-canvas {
  position: relative;
  width: 100%;
  height: 100%;
  outline: none;
}

.canvas-toolbar {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
</style>
