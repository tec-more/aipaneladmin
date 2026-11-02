<template>
  <!-- 版本快照只读预览（T13）：独立 VueFlow 实例渲染 graph_json，不进 canvasStore -->
  <div class="snapshot-preview">
    <VueFlow
      :nodes="nodes"
      :edges="edges"
      :node-types="nodeTypes"
      :nodes-draggable="false"
      :nodes-connectable="false"
      :edges-updatable="false"
      :elements-selectable="false"
      :min-zoom="0.2"
      :max-zoom="2"
      fit-view-on-init
      class="snapshot-flow"
    >
      <Background :gap="20" pattern-color="#e4e7ed" />
      <Controls :show-interactive="false" />
    </VueFlow>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { toVueFlow } from '@/utils/graphSerializer'
import { nodeTypes } from '@/components/canvas/nodes/nodeTypes'

const props = defineProps({
  /** 版本快照 graph_json（Schema v2） */
  graph: { type: Object, default: () => ({}) }
})

const converted = computed(() => toVueFlow(props.graph || {}))
const nodes = computed(() => converted.value.nodes)
const edges = computed(() => converted.value.edges)
</script>

<style scoped lang="scss">
.snapshot-preview {
  width: 100%;
  height: 420px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}
.snapshot-flow { width: 100%; height: 100%; background: #fafbfc; }
</style>
