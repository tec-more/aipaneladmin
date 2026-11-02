<template>
  <!-- 变量插值助手：{{}} 光标插入 + 占位符提取提示；不做引擎求值 -->
  <div class="var-editor">
    <el-input
      ref="inputRef"
      :model-value="modelValue"
      type="textarea" :rows="5"
      @update:model-value="emit('update:modelValue', $event)"
    />
    <div class="var-toolbar">
      <el-button size="small" text type="primary" @click="insertPlaceholder">
        <el-icon><Plus /></el-icon>插入变量
      </el-button>
      <span v-if="placeholders.length" class="var-hint">
        占位符：
        <code v-for="p in placeholders" :key="p" class="var-tag">{{ p }}</code>
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  variables: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue'])

const inputRef = ref(null)

/** 提取 {{xxx}} 占位符（prompt_vars 键一致性前端提示数据源） */
const placeholders = computed(() => {
  const hits = props.modelValue.match(/\{\{[^{}]+\}\}/g) || []
  return [...new Set(hits)]
})

/** 在光标处插入 {{}}，并把光标置于占位符内部 */
async function insertPlaceholder() {
  const textarea = inputRef.value?.textarea
  const text = props.modelValue || ''
  const pos = textarea?.selectionStart ?? text.length
  const next = `${text.slice(0, pos)}{{}}${text.slice(pos)}`
  emit('update:modelValue', next)
  await nextTick()
  if (textarea) {
    textarea.focus()
    textarea.setSelectionRange(pos + 2, pos + 2)
  }
}
</script>

<style scoped>
.var-toolbar { display: flex; align-items: center; gap: 8px; margin-top: 4px; flex-wrap: wrap; }
.var-hint { font-size: 12px; color: var(--el-text-color-secondary); }
.var-tag {
  background: var(--el-fill-color-light); border-radius: 3px;
  padding: 0 4px; margin-right: 4px; font-size: 11px;
}
</style>
