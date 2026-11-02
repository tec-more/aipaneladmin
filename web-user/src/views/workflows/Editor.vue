<template>
  <!-- 工作流编辑器：Library + Canvas + ConfigShell + ProblemPanel 四区（T8 节点2 §1） -->
  <div v-loading="loading" class="editor-page">
    <!-- 顶栏 -->
    <header class="editor-header">
      <div class="header-left">
        <el-button :icon="Back" text @click="onBack">返回</el-button>
        <el-divider direction="vertical" />
        <span class="workflow-name">{{ canvasStore.meta.name }}</span>
        <el-tag v-if="canvasStore.dirty" size="small" type="warning" effect="plain">未保存</el-tag>
      </div>
      <div class="header-right">
        <!-- T13 发布状态徽标 -->
        <el-tag v-if="wfStatus === 'active'" size="small" type="success" effect="plain">已发布 v{{ currentVersionNo }}</el-tag>
        <el-tag v-else-if="wfStatus === 'disabled'" size="small" type="warning" effect="plain">已停用</el-tag>
        <el-tag v-else size="small" type="info" effect="plain">草稿</el-tag>
        <span v-if="canvasStore.lastSavedAt" class="saved-hint">
          已保存 {{ formatTime(canvasStore.lastSavedAt) }}
        </span>
        <el-button :icon="DocumentChecked" :loading="validating" @click="onServerValidate">校验</el-button>
        <el-button :icon="Tickets" @click="versionRef?.load(); versionVisible = true">版本</el-button>
        <el-button type="primary" :icon="Upload" :loading="canvasStore.saving" @click="onSave()">保存</el-button>
        <el-button type="success" :icon="Promotion" :disabled="canvasStore.hasBlockingIssues" @click="publishRef?.open(canvasStore.workflowId)">发布</el-button>
      </div>
    </header>

    <!-- 主体 -->
    <div class="editor-body">
      <NodeLibrary />
      <div class="editor-center">
        <!-- T12 试跑控制条 -->
        <RunPanel
          @run="onRun"
          @toggle-trace="traceVisible = !traceVisible"
          @hitl="hitlRef?.open()"
        />
        <div class="canvas-wrap">
          <WorkflowCanvas :readonly="execStore.running" />
        </div>
        <ProblemPanel @locate="onLocateNode" />
      </div>
      <ConfigPanelShell />
    </div>

    <!-- T12 试跑/Trace/HITL -->
    <InputsDialog ref="inputsRef" :inputs="startInputs" :starting="execStore.status === 'connecting'" @confirm="onConfirmRun" />
    <TracePanel v-model="traceVisible" />
    <HitlDialog ref="hitlRef" />

    <!-- T13 发布/版本 -->
    <PublishDialog ref="publishRef" @published="onPublished" @blocked="onPublishBlocked" />
    <VersionDrawer ref="versionRef" v-model="versionVisible" :workflow-id="canvasStore.workflowId" :active-no="currentVersionNo" @changed="onVersionChanged" />
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch, computed } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Back, Upload, DocumentChecked, Promotion, Tickets } from '@element-plus/icons-vue'
import { useVueFlow } from '@vue-flow/core'
import { getNodeMeta } from '@validator'
import { getWorkflowDetail, saveDraft, validateWorkflow } from '@/api/workflow'
import { useCanvasStore } from '@/stores/canvas'
import { useResourceStore } from '@/stores/resource'
import { useExecutionStore } from '@/stores/execution'
import NodeLibrary from '@/components/canvas/NodeLibrary.vue'
import WorkflowCanvas from '@/components/canvas/WorkflowCanvas.vue'
import ConfigPanelShell from '@/components/canvas/ConfigPanelShell.vue'
import ProblemPanel from '@/components/canvas/ProblemPanel.vue'
import RunPanel from '@/components/canvas/run/RunPanel.vue'
import InputsDialog from '@/components/canvas/run/InputsDialog.vue'
import TracePanel from '@/components/canvas/run/TracePanel.vue'
import HitlDialog from '@/components/canvas/run/HitlDialog.vue'
import PublishDialog from '@/components/canvas/publish/PublishDialog.vue'
import VersionDrawer from '@/components/canvas/publish/VersionDrawer.vue'

const AUTOSAVE_DELAY = 1500 // T8 节点1 裁定 Q2：1.5s 防抖

const route = useRoute()
const router = useRouter()
const canvasStore = useCanvasStore()
const execStore = useExecutionStore()
const { setCenter } = useVueFlow()

const loading = ref(false)
const validating = ref(false)
const traceVisible = ref(false)
const inputsRef = ref(null)
const hitlRef = ref(null)
// T13 发布/版本
const publishRef = ref(null)
const versionRef = ref(null)
const versionVisible = ref(false)
const wfStatus = ref('draft')
const currentVersionNo = ref(null)
let autosaveTimer = null

function formatTime(t) {
  return new Date(t).toLocaleTimeString('zh-CN', { hour12: false })
}

// ---- 装载 ----
async function loadDetail() {
  loading.value = true
  try {
    const res = await getWorkflowDetail(route.params.id)
    // BUG-T15-006：统一包络解包（loadDetail 需要解包后的 data 段）
    canvasStore.loadDetail(res?.data ?? res)
    canvasStore.runLocalValidate()
    // T13：发布状态/当前版本（字段多别名兜底，后端以 current_version 为准）
    const d = res?.data ?? res
    wfStatus.value = d?.status || 'draft'
    currentVersionNo.value = d?.current_version_no ?? d?.current_version ?? null
  } catch {
    // 404（M8 归属不命中按不存在）→ 回列表
    router.replace({ name: 'WorkflowList' })
  } finally {
    loading.value = false
  }
}

// ---- T13 发布回调 ----
function onPublished(data) {
  wfStatus.value = 'active'
  if (data?.version_no) currentVersionNo.value = data.version_no
  // 发布成功后草稿可能已被服务端标记，重新拉取保持乐观锁一致
  loadDetail()
}

/** 发布被服务端校验阻断：issues 注入问题面板（C9 双源） */
function onPublishBlocked(issues) {
  canvasStore.serverIssues = issues || []
  ElMessage.error('发布被阻断，请解决问题后重试')
}

/** 版本变更（回滚/停用）：刷新状态与详情 */
function onVersionChanged() {
  loadDetail()
}

// ---- 保存（乐观锁 + 409/422 处理）----
async function doSave() {
  if (canvasStore.saving || !canvasStore.workflowId) return
  canvasStore.saving = true
  try {
    const res = await saveDraft(canvasStore.workflowId, {
      graph_json: canvasStore.collectGraph(),
      draft_version: canvasStore.draftVersion
    })
    // BUG-T15-006：统一包络解包（markSaved 需要解包后的 draft_version）
    canvasStore.markSaved(res?.data ?? res)
  } catch (err) {
    const code = err?.data?.error?.code
    if (code === 40901) {
      // 乐观锁冲突（P2）：引导刷新，不自动覆盖他人修改
      ElMessageBox.confirm(
        '草稿版本已变化（可能在其他页面编辑过）。刷新将放弃当前未保存修改，是否刷新？',
        '版本冲突',
        { type: 'warning', confirmButtonText: '刷新', cancelButtonText: '保留当前' }
      ).then(() => loadDetail()).catch(() => {})
    } else if (code === 42200) {
      // 服务端校验阻断：issues 注入问题面板
      canvasStore.serverIssues = err?.data?.error?.details?.issues || []
      ElMessage.error('存在阻断问题，请查看底部问题面板')
    }
    // 其余错误拦截器已提示
  } finally {
    canvasStore.saving = false
  }
}

function onSave() {
  canvasStore.runLocalValidate()
  doSave()
}

/** 防抖自动保存（C10/4.7）：dirty 变化触发，保存中跳过并在完成后补一轮 */
watch(
  () => canvasStore.dirty,
  (dirty) => {
    if (!dirty) return
    clearTimeout(autosaveTimer)
    autosaveTimer = setTimeout(() => {
      if (canvasStore.dirty && !canvasStore.saving) doSave()
    }, AUTOSAVE_DELAY)
  }
)

// ---- 服务端校验（E-108/E-110 等 server-only 项）----
async function onServerValidate() {
  validating.value = true
  try {
    const res = await validateWorkflow(canvasStore.workflowId, canvasStore.collectGraph())
    // BUG-T15-006：统一包络解包
    const d = res?.data ?? res
    canvasStore.serverIssues = d?.issues || []
    canvasStore.serverSummary = d || null
    // BUG-T15-007：契约对齐（后端返回 valid/error_count/warning_count，非 ok/summary.error）
    if (d?.valid) {
      ElMessage.success('校验通过')
    } else {
      ElMessage.warning(`校验未通过：${d?.error_count ?? 0} 个错误`)
    }
  } catch {
    // 拦截器已提示
  } finally {
    validating.value = false
  }
}

// ---- 问题定位：居中节点（C9）----
function onLocateNode(nodeId) {
  const node = canvasStore.nodes.find((n) => n.id === nodeId)
  if (node) setCenter(node.position.x + 84, node.position.y + 30, { zoom: 1, duration: 300 })
}

// ---- T12 试跑 ----
/** start 节点输入端口声明（无 inputs 则空数组，直接试跑） */
const startInputs = computed(() => {
  const start = canvasStore.nodes.find((n) => n.data?.nodeType === 'start')
  if (!start) return []
  if (Array.isArray(start.data?.inputs) && start.data.inputs.length) return start.data.inputs
  return getNodeMeta('start')?.inputs || []
})

function onRun() {
  canvasStore.runLocalValidate()
  if (canvasStore.hasBlockingIssues) {
    ElMessage.error('存在阻断问题，请先解决后再试跑')
    return
  }
  if (startInputs.value.length) {
    inputsRef.value?.open()
  } else {
    onConfirmRun({})
  }
}

async function onConfirmRun(inputs) {
  inputsRef.value?.close()
  traceVisible.value = true
  // SSE 归约在 store 内；422/429 等错误在 store.start 捕获前由 fetch 抛出
  try {
    await execStore.start(canvasStore.workflowId, inputs)
  } catch (e) {
    if (e?.status === 42200 || e?.status === 422) {
      ElMessage.error('服务端校验未通过，无法试跑')
    } else if (e?.status === 429) {
      ElMessage.error(e.message || '额度不足或并发超限')
    } else if (e?.status) {
      ElMessage.error(e.message || '试跑失败')
    }
  }
}

// HITL 挂起（流式归约实时触发，含流内与流结束后两种时序）→ 自动弹审批
watch(() => execStore.status, (s) => {
  if (s === 'paused' && execStore.hitl) hitlRef.value?.open()
})

// ---- 离开保护（4.7）----
function onBack() {
  if (!canvasStore.dirty) {
    router.push({ name: 'WorkflowList' })
    return
  }
  ElMessageBox.confirm('存在未保存修改，离开前是否保存？', '提示', {
    type: 'warning',
    confirmButtonText: '保存并离开',
    cancelButtonText: '直接离开',
    distinguishCancelAndClose: true,
    showClose: false
  }).then(async () => {
    await doSave()
    router.push({ name: 'WorkflowList' })
  }).catch((action) => {
    if (action === 'cancel') router.push({ name: 'WorkflowList' })
  })
}

onBeforeRouteLeave(() => {
  execStore.reset()
  canvasStore.reset()
})

function onBeforeUnload(e) {
  if (canvasStore.dirty) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  loadDetail()
  // T11：加载 node_type 授权集，驱动节点库受限节点（hitl/sub_agent/tool）动态置灰
  useResourceStore().load('node_type').catch(() => {})
  window.addEventListener('beforeunload', onBeforeUnload)
})

onBeforeUnmount(() => {
  clearTimeout(autosaveTimer)
  window.removeEventListener('beforeunload', onBeforeUnload)
})
</script>

<style scoped lang="scss">
.editor-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f7fa;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 52px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.workflow-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.saved-hint {
  font-size: 12px;
  color: #909399;
}

.editor-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

.editor-center {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

/* T12 试跑：画布容器（只读由 WorkflowCanvas readonly prop 控制） */
.canvas-wrap {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}
</style>
