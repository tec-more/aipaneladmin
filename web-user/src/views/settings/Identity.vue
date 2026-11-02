<template>
  <!-- 关联管理页（T14）：PRD §3.3 关联管理页产品定义 -->
  <div class="page-card">
    <div class="page-header">
      <h2 class="page-title">关联管理</h2>
      <el-button :icon="Refresh" :loading="loading" @click="loadStatus">刷新</el-button>
    </div>

    <el-skeleton v-if="loading && !statusData" :rows="4" animated />

    <template v-else>
      <LinkStatusCard
        :status="status"
        :peer="peer"
        :linked-at="linkedAt"
        :dismissed-until="dismissedUntil"
        :reason-message="reasonMessage"
        @link="openLinkDialog"
        @unlink="openUnlinkDialog"
        @dismiss="onDismiss"
        @resume="onResume"
      />

      <el-card class="desc-card" shadow="never">
        <template #header>
          <span class="desc-title">关联说明</span>
        </template>
        <ul class="desc-list">
          <li>关联仅用于身份识别，不共享工作流、知识库、额度与账单。</li>
          <li>建立关联需验证对方主体归属（密码或邮箱验证码），系统不会自动绑定。</li>
          <li>解除关联后进入 30 天冷却期，期间不再提示关联。</li>
          <li>选择"不再提示"后 30 天内不再展示关联提示，期满自动恢复。</li>
        </ul>
      </el-card>

      <!-- T14+ K4：操作历史（L10 用户可查） -->
      <el-card class="audit-card" shadow="never">
        <template #header>
          <span class="desc-title">操作历史</span>
          <el-button
            text
            size="small"
            :icon="Refresh"
            :loading="auditLoading"
            class="audit-refresh"
            @click="loadAudit"
          >
            刷新
          </el-button>
        </template>
        <el-table v-loading="auditLoading" :data="auditList" size="small">
          <el-table-column prop="at" label="时间" width="170">
            <template #default="{ row }">{{ formatTime(row.at) }}</template>
          </el-table-column>
          <el-table-column prop="action" label="操作" width="160">
            <template #default="{ row }">
              <el-tag size="small" :type="actionTagType(row.action)" effect="light">
                {{ actionLabel(row.action) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="actor" label="操作者" width="120" show-overflow-tooltip />
          <el-table-column label="备注" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ detailText(row) }}</template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无操作记录" :image-size="60" />
          </template>
        </el-table>
      </el-card>
    </template>

    <VerifyDialog ref="verifyDialogRef" @success="onVerifySuccess" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getLinkStatus, dismissIdentity, resumeIdentity, getIdentityAudit } from '@/api/identity'
import LinkStatusCard from '@/components/identity/LinkStatusCard.vue'
import VerifyDialog from '@/components/identity/VerifyDialog.vue'

/**
 * 关联管理页（T14 + T14+ K2/K4）
 * PRD §3.3 关联管理页：
 * - 状态：未关联 / 已关联 / 冷却中 / 不再提示
 * - 操作：关联账号 / 解除关联 / 不再提示 / 重新开启提示（T14+ K2）
 * - 操作历史：L10 用户可查（T14+ K4）
 * - 说明：明示"关联仅用于身份识别，不共享工作流、知识库、额度与账单"
 */
const loading = ref(false)
const statusData = ref(null)
const verifyDialogRef = ref(null)

const status = computed(() => statusData.value?.status || 'none')
const peer = computed(() => statusData.value?.peer || null)
const linkedAt = computed(() => statusData.value?.linked_at || null)
const dismissedUntil = computed(() => statusData.value?.dismissed_until || null)
const reasonMessage = computed(() => statusData.value?.message || '')

async function loadStatus() {
  loading.value = true
  try {
    const res = await getLinkStatus()
    statusData.value = res?.data ?? null
  } catch {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
}

function openLinkDialog() {
  verifyDialogRef.value?.open('link', peer.value)
}

function openUnlinkDialog() {
  verifyDialogRef.value?.open('unlink', peer.value)
}

async function onDismiss() {
  try {
    await ElMessageBox.confirm(
      '选择"不再提示"后，30 天内系统不会再展示关联提示，期满自动恢复。是否继续？',
      '不再提示',
      { type: 'warning', confirmButtonText: '不再提示', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await dismissIdentity()
    ElMessage.success('已设置不再提示，30 天后自动恢复')
    loadStatus()
    loadAudit()
  } catch {
    // 拦截器已提示
  }
}

// T14+ K2：重新开启提示
async function onResume() {
  try {
    await ElMessageBox.confirm(
      '重新开启后，系统将再次展示关联提示。是否继续？',
      '重新开启提示',
      { type: 'info', confirmButtonText: '重新开启', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await resumeIdentity()
    ElMessage.success('已重新开启提示')
    loadStatus()
    loadAudit()
  } catch {
    // 拦截器已提示
  }
}

function onVerifySuccess() {
  loadStatus()
  loadAudit()
}

// ============ T14+ K4：操作历史 ============
const auditLoading = ref(false)
const auditList = ref([])

const ACTION_LABELS = {
  prompt_shown: '提示已展示',
  link_initiated: '发起关联',
  verify_failed: '验证失败',
  linked: '关联成功',
  dismissed: '不再提示',
  resumed: '重新开启提示',
  unlinked: '解除关联',
  admin_bind: '管理员代绑'
}

function actionLabel(a) {
  return ACTION_LABELS[a] || a
}

function actionTagType(a) {
  if (a === 'linked' || a === 'resumed') return 'success'
  if (a === 'verify_failed') return 'danger'
  if (a === 'dismissed' || a === 'unlinked') return 'warning'
  return 'info'
}

function detailText(row) {
  const d = row?.detail
  if (!d || typeof d !== 'object') return '—'
  const parts = []
  if (d.via) parts.push(`方式=${d.via}`)
  if (d.reason) parts.push(`原因=${d.reason}`)
  if (d.attempts_left !== undefined) parts.push(`剩余次数=${d.attempts_left}`)
  if (d.duration) parts.push(`时长=${d.duration}`)
  return parts.join('；') || '—'
}

function formatTime(t) {
  return t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '—'
}

async function loadAudit() {
  auditLoading.value = true
  try {
    const res = await getIdentityAudit()
    auditList.value = res?.data?.items || []
  } catch {
    auditList.value = []
  } finally {
    auditLoading.value = false
  }
}

onMounted(() => {
  loadStatus()
  loadAudit()
})
</script>

<style scoped lang="scss">
.page-card {
  background: #fff;
  border: 1px solid var(--u-border);
  border-radius: 8px;
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--u-text-main);
}

.desc-card {
  margin-top: 16px;
  border: 1px solid var(--u-border);
}

.audit-card {
  margin-top: 16px;
  border: 1px solid var(--u-border);
}

.audit-refresh {
  margin-left: 8px;
}

.desc-title {
  font-size: 14px;
  font-weight: 600;
}

.desc-list {
  margin: 0;
  padding-left: 18px;
  color: var(--u-text-sub);
  font-size: 13px;
  line-height: 24px;
}
</style>
