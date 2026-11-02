<template>
  <!-- 子工作流选择器（T11 裁定 A）：复用 M8 归属模型，拉取自己的工作流，非授权模型 -->
  <div class="workflow-select">
    <div class="ws-trigger" @click="open">
      <span v-if="selectedLabel" class="ws-label">{{ selectedLabel }}</span>
      <span v-else class="ws-placeholder">{{ placeholder }}</span>
      <el-icon class="ws-open"><Setting /></el-icon>
    </div>

    <el-dialog v-model="visible" title="选择子工作流" width="520px" append-to-body>
      <el-input v-model="keyword" placeholder="搜索工作流" clearable class="ws-search">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>

      <div v-loading="loading" class="ws-list">
        <el-empty v-if="!loading && !filtered.length" description="暂无可用工作流" :image-size="60" />
        <div
          v-for="wf in filtered" :key="wf.id"
          class="ws-item" :class="{ 'is-active': String(currentId) === String(wf.id) }"
          @click="choose(wf)"
        >
          <div class="ws-item-main">
            <div class="ws-item-name">{{ wf.name }}</div>
            <div class="ws-item-desc">{{ wf.description || '—' }}</div>
          </div>
          <el-tag v-if="wf.status" size="small" :type="wf.status === 'published' ? 'success' : 'info'">
            {{ wf.status }}
          </el-tag>
        </div>
      </div>

      <template #footer>
        <el-button @click="visible = false">取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 子工作流选择器（T11 裁定 A）
 * 数据源：GET /u/workflows（M8 归属，仅返回当前主体 own/linked 工作流）。
 * 与 ResourceSelect 区别：子工作流是"自己的资源"，归属校验非资源授权。
 */
import { ref, computed } from 'vue'
import { getMyWorkflows } from '@/api/workflow'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  placeholder: { type: String, default: '选择子工作流' }
})
const emit = defineEmits(['update:modelValue'])

const visible = ref(false)
const loading = ref(false)
const keyword = ref('')
const list = ref([])

const currentId = computed(() => props.modelValue)
const filtered = computed(() => {
  const k = keyword.value.trim().toLowerCase()
  if (!k) return list.value
  return list.value.filter((w) => (w.name || '').toLowerCase().includes(k))
})
const selectedLabel = computed(() => {
  const hit = list.value.find((w) => String(w.id) === String(currentId.value))
  return hit ? hit.name : (currentId.value ? `#${currentId.value}` : '')
})

async function open() {
  visible.value = true
  keyword.value = ''
  loading.value = true
  try {
    const res = await getMyWorkflows({ page: 1, page_size: 100 })
    list.value = res.data?.list || res.data?.items || []
  } finally {
    loading.value = false
  }
}
function choose(wf) {
  emit('update:modelValue', String(wf.id))
  visible.value = false
}
</script>

<style scoped>
.workflow-select { width: 100%; }
.ws-trigger {
  min-height: 32px; display: flex; align-items: center;
  padding: 4px 8px; border: 1px solid var(--el-border-color); border-radius: 4px;
  cursor: pointer; transition: border-color .15s;
}
.ws-trigger:hover { border-color: var(--el-color-primary); }
.ws-label { font-size: 13px; color: var(--el-text-color-primary); }
.ws-placeholder { color: var(--el-text-color-placeholder); font-size: 13px; }
.ws-open { margin-left: auto; color: var(--el-text-color-secondary); }
.ws-search { margin-bottom: 10px; }
.ws-list { max-height: 320px; overflow-y: auto; }
.ws-item {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px;
  border: 1px solid var(--el-border-color-lighter); border-radius: 4px;
  margin-bottom: 6px; cursor: pointer; transition: all .15s;
}
.ws-item:hover { border-color: var(--el-color-primary-light-5); }
.ws-item.is-active { border-color: var(--el-color-primary); background: var(--el-color-primary-light-9); }
.ws-item-main { flex: 1; min-width: 0; }
.ws-item-name { font-size: 13px; color: var(--el-text-color-primary); }
.ws-item-desc { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
