<template>
  <!-- 降级/未知节点只读兜底（K10）：保留 config 原文展示，提示人工处理 -->
  <div class="readonly-config">
    <el-alert type="warning" :closable="false" show-icon class="tip">
      该节点类型在当前用户域无注册元数据（可能为 v1 转换降级节点）。
      配置以原文展示，请按问题面板提示重建连线或替换节点。
    </el-alert>
    <pre class="config-json">{{ formatted }}</pre>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  config: { type: Object, default: () => ({}) }
})
const formatted = computed(() => JSON.stringify(props.config ?? {}, null, 2))
</script>

<style scoped>
.tip { margin-bottom: 12px; }
.config-json {
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding: 12px;
  font-size: 12px;
  line-height: 1.6;
  overflow: auto;
  max-height: 320px;
  margin: 0;
}
</style>
