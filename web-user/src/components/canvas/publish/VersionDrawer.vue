<template>
  <!-- 版本抽屉（T13）：版本列表 + 快照只读预览 + 回滚/停用（后端语义：回滚生成新发布版本，不改草稿） -->
  <el-drawer :model-value="modelValue" title="版本管理" size="560px" @update:model-value="$emit('update:modelValue', $event)" @open="load">
    <div v-loading="loading" class="version-body">
      <el-empty v-if="!versions.length && !loading" description="暂无发布版本" :image-size="80" />
      <template v-else>
        <div
          v-for="v in versions"
          :key="v.version_no"
          class="version-item"
          :class="{ 'is-active': activeNo === v.version_no }"
        >
          <div class="version-head" @click="toggle(v.version_no)">
            <el-tag size="small" :type="v.status === 'published' ? 'success' : 'info'" effect="dark">v{{ v.version_no }}</el-tag>
            <el-tag v-if="v.status === 'disabled'" size="small" type="warning" effect="plain">已停用</el-tag>
            <span class="version-time">{{ formatTime(v.published_at || v.created_at) }}</span>
            <el-icon class="version-caret" :class="{ open: expandedNo === v.version_no }"><ArrowRight /></el-icon>
          </div>
          <div v-if="v.description" class="version-desc">{{ v.description }}</div>

          <!-- 展开：快照预览 + 动作 -->
          <div v-if="expandedNo === v.version_no" class="version-detail">
            <SnapshotPreview v-if="snapshot" :graph="snapshot.graph_json" />
            <div v-else v-loading="true" style="height:60px" />
            <div class="version-actions">
              <el-button size="small" type="warning" plain :loading="acting" @click="onRollback(v)">回滚到此版本</el-button>
            </div>
          </div>
        </div>
      </template>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight } from '@element-plus/icons-vue'
import { listVersions, getVersionSnapshot, rollbackWorkflow } from '@/api/workflow'
import SnapshotPreview from './SnapshotPreview.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  workflowId: { type: [Number, String], required: true },
  /** 当前发布版本号（列表接口 current_version） */
  activeNo: { type: Number, default: null }
})
const emit = defineEmits(['update:modelValue', 'changed'])

const loading = ref(false)
const acting = ref(false)
const versions = ref([])
const expandedNo = ref(null)
const snapshot = ref(null)

function formatTime(t) {
  return t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '-'
}

async function load() {
  loading.value = true
  try {
    const res = await listVersions(props.workflowId)
    versions.value = res?.data ?? res ?? []
  } catch { /* 拦截器已提示 */ } finally {
    loading.value = false
  }
}

async function toggle(no) {
  if (expandedNo.value === no) { expandedNo.value = null; snapshot.value = null; return }
  expandedNo.value = no
  snapshot.value = null
  try {
    const res = await getVersionSnapshot(props.workflowId, no)
    snapshot.value = res?.data ?? res
  } catch { /* 拦截器已提示 */ }
}

/** 回滚（后端：以旧版 graph_json 生成新发布版本；不影响草稿） */
function onRollback(v) {
  ElMessageBox.confirm(
    `将以 v${v.version_no} 的内容生成一个新的发布版本（旧版本不可变，不影响当前草稿）。确认回滚？`,
    '回滚确认',
    { type: 'warning', confirmButtonText: '确认回滚', cancelButtonText: '取消' }
  ).then(async () => {
    acting.value = true
    try {
      const res = await rollbackWorkflow(props.workflowId, v.version_no)
      const data = res?.data ?? res
      ElMessage.success(`回滚成功，已生成新版本 v${data?.version_no}`)
      await load()
      emit('changed')
    } catch (err) {
      if (err?.data?.error?.code === 42200) {
        ElMessage.error('回滚被阻断：旧版本引用的资源已失效')
      }
    } finally {
      acting.value = false
    }
  }).catch(() => {})
}

defineExpose({ load })
</script>

<style scoped lang="scss">
.version-body { padding: 4px; }
.version-item {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 10px;
  &.is-active { border-color: var(--el-color-success); }
}
.version-head { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.version-time { color: #909399; font-size: 12px; flex: 1; }
.version-caret { transition: transform 0.2s; color: #c0c4cc; }
.version-caret.open { transform: rotate(90deg); }
.version-desc { margin-top: 6px; font-size: 12px; color: #606266; }
.version-detail { margin-top: 10px; }
.version-actions { margin-top: 10px; display: flex; justify-content: flex-end; }
</style>
