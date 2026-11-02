<template>
  <!-- 授权资源选择器（T11）：替换 resource_ref 文本占位 -->
  <div class="resource-select">
    <!-- 已选摘要 + 打开弹窗按钮 -->
    <div class="rs-trigger" @click="open">
      <template v-if="selectedLabels.length">
        <el-tag
          v-for="(label, i) in selectedLabels" :key="i"
          size="small" class="rs-tag" closable @close.stop="removeAt(i)"
        >{{ label }}</el-tag>
      </template>
      <span v-else class="rs-placeholder">{{ placeholder }}</span>
      <el-icon class="rs-open"><Setting /></el-icon>
    </div>

    <el-dialog v-model="visible" :title="`选择${kindLabel}`" width="520px" append-to-body>
      <el-input v-model="keyword" :placeholder="`搜索${kindLabel}`" clearable class="rs-search">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>

      <div v-loading="loading" class="rs-list">
        <el-empty v-if="!loading && !filtered.length" :description="`暂无已授权${kindLabel}`" :image-size="60" />
        <div
          v-for="item in filtered" :key="item.id"
          class="rs-item" :class="{ 'is-active': isChecked(item.id) }"
          @click="toggle(item.id)"
        >
          <el-checkbox :model-value="isChecked(item.id)" @click.stop @change="toggle(item.id)" />
          <div class="rs-item-main">
            <div class="rs-item-label">{{ item.label }}</div>
            <div class="rs-item-extra">{{ extraText(item) }}</div>
          </div>
          <el-tooltip v-if="item.expires_at" :content="`授权至 ${item.expires_at}`" placement="left">
            <el-icon class="rs-expire"><Clock /></el-icon>
          </el-tooltip>
        </div>
      </div>

      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="confirm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 授权资源选择器（T11）
 * 数据源：resourceStore（会话级缓存）。支持单/多选（依字段类型）。
 * 授权判定权威在服务端 E-110，本组件仅做选择视图。
 */
import { ref, computed } from 'vue'
import { useResourceStore } from '@/stores/resource'

const props = defineProps({
  modelValue: { type: [String, Array], default: '' },
  /** 'model'|'kb'|'tool'|'agent' */
  resourceType: { type: String, required: true },
  /** 字段类型：'array<...>' 多选，否则单选 */
  fieldType: { type: String, default: 'string' },
  placeholder: { type: String, default: '点击选择' }
})
const emit = defineEmits(['update:modelValue'])

const store = useResourceStore()
const visible = ref(false)
const loading = ref(false)
const keyword = ref('')
const checked = ref([])

const multiple = computed(() => props.fieldType.startsWith('array'))
const kindLabel = computed(() => ({ model: '模型', kb: '知识库', tool: '工具', agent: '子Agent' }[props.resourceType] || '资源'))
const items = computed(() => store.itemsOf(props.resourceType))
const filtered = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  if (!k) return items.value
  return items.value.filter((i) => (i.label || '').toLowerCase().includes(k))
})
const selectedIds = computed(() => (multiple.value ? (Array.isArray(props.modelValue) ? props.modelValue : []) : (props.modelValue ? [props.modelValue] : [])))
const selectedLabels = computed(() => selectedIds.value.map((id) => labelOf(id)))

function labelOf(id) {
  const hit = items.value.find((i) => String(i.id) === String(id))
  return hit ? hit.label : `${id}（未授权/已失效）`
}
function extraText(item) {
  const e = item.extra || {}
  return e.provider || e.tag?.join?.('、') || e.status || ''
}
function isChecked(id) { return checked.value.map(String).includes(String(id)) }

async function open() {
  visible.value = true
  keyword.value = ''
  checked.value = [...selectedIds.value]
  if (!store.isLoaded(props.resourceType)) {
    loading.value = true
    try { await store.load(props.resourceType) } finally { loading.value = false }
  }
}
function toggle(id) {
  const sid = String(id)
  if (multiple.value) {
    const idx = checked.value.map(String).indexOf(sid)
    if (idx >= 0) checked.value.splice(idx, 1)
    else checked.value.push(id)
  } else {
    checked.value = [id]
  }
}
function removeAt(i) {
  const next = [...selectedIds.value]
  const removed = next.splice(i, 1)[0]
  emit('update:modelValue', multiple.value ? next : (next[0] ?? ''))
  void removed
}
function confirm() {
  emit('update:modelValue', multiple.value ? [...checked.value] : (checked.value[0] ?? ''))
  visible.value = false
}
</script>

<style scoped>
.resource-select { width: 100%; }
.rs-trigger {
  min-height: 32px; display: flex; align-items: center; flex-wrap: wrap; gap: 4px;
  padding: 4px 8px; border: 1px solid var(--el-border-color); border-radius: 4px;
  cursor: pointer; transition: border-color .15s;
}
.rs-trigger:hover { border-color: var(--el-color-primary); }
.rs-tag { margin: 0; }
.rs-placeholder { color: var(--el-text-color-placeholder); font-size: 13px; }
.rs-open { margin-left: auto; color: var(--el-text-color-secondary); }
.rs-search { margin-bottom: 10px; }
.rs-list { max-height: 320px; overflow-y: auto; }
.rs-item {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  border: 1px solid var(--el-border-color-lighter); border-radius: 4px;
  margin-bottom: 6px; cursor: pointer; transition: all .15s;
}
.rs-item:hover { border-color: var(--el-color-primary-light-5); }
.rs-item.is-active { border-color: var(--el-color-primary); background: var(--el-color-primary-light-9); }
.rs-item-main { flex: 1; min-width: 0; }
.rs-item-label { font-size: 13px; color: var(--el-text-color-primary); }
.rs-item-extra { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px; }
.rs-expire { color: var(--el-color-warning); }
</style>
