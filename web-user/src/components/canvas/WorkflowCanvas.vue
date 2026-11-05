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
import dagre from '@dagrejs/dagre'
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

/** dagre 分层自动布局：LR 主轴、自动压缩连线交叉、按子树分配行距 */
function autoLayout() {
  const nodes = canvasStore.nodes
  if (!nodes.length) return
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'LR', nodesep: 50, ranksep: 140, marginx: 40, marginy: 40 })
  g.setDefaultEdgeLabel(() => ({}))
  // 优先用 VueFlow 已测量的实际节点尺寸（含端口行高），缺省 180x56 兜底
  for (const n of nodes) {
    const w = n.dimensions?.width || n.width || 180
    const h = n.dimensions?.height || n.height || 56
    g.setNode(n.id, { width: w, height: h })
  }
  for (const e of canvasStore.edges) {
    if (g.hasNode(e.source) && g.hasNode(e.target)) g.setEdge(e.source, e.target)
  }
  dagre.layout(g)
  canvasStore.snapshot()
  // dagre 返回中心点坐标，VueFlow 需要左上角
  nodes.forEach((n) => {
    const pos = g.node(n.id)
    if (!pos) return
    const w = n.dimensions?.width || n.width || 180
    const h = n.dimensions?.height || n.height || 56
    n.position = { x: Math.round(pos.x - w / 2), y: Math.round(pos.y - h / 2) }
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

/* VueFlow 的 paneClick 仅当 event.target === pane 本身时触发（wrapHandler 丢弃其它 target）。
   Background 的 svg 铺满画布且 z-index 高于 pane，不放开的话空白处点击永远到不了 pane，
   pane-click -> clearSelection（关闭右侧配置面板）失效。 */
.workflow-canvas :deep(.vue-flow__background) {
  pointer-events: none;
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
