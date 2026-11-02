<template>
  <div v-if="authStore.shouldShowLinkHint" class="link-hint-card">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="link-hint-alert"
    >
      <template #title>
        <span class="hint-text">
          检测到该邮箱存在可关联的{{ peerTypeText }}<template v-if="peerText">（{{ peerText }}）</template>，关联后仅用于身份识别，不共享工作流、知识库与额度。
        </span>
        <span class="hint-actions">
          <el-button type="primary" link @click="goIdentity">立即关联</el-button>
          <el-button link @click="dismissSession">暂不关联</el-button>
          <el-button link :loading="dismissing" @click="dismissForever">不再提示</el-button>
        </span>
      </template>
    </el-alert>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getLinkStatus, dismissIdentity } from '@/api/identity'

/**
 * 身份关联提示卡（PRD §3.3，T14 增强）
 * L2：非阻塞提示卡（页面顶部），默认焦点为"暂不关联"；
 * L3：仅展示脱敏信息（主体类型、用户名、打码邮箱），不展示资产数据；
 * L4："暂不关联"仅本次会话生效；"不再提示"调 dismiss API，30 天内不再提示；
 * R-14：不触发任何自动绑定，"立即关联"仅跳转关联管理页。
 */
const router = useRouter()
const authStore = useAuthStore()

const peer = ref(null)
const dismissing = ref(false)

const peerTypeText = computed(() => {
  if (!peer.value) return '账号'
  return peer.value.owner_type === 'usr' ? '后台账号' : '客户账号'
})

const peerText = computed(() => {
  if (!peer.value) return ''
  const parts = []
  if (peer.value.username) parts.push(peer.value.username)
  if (peer.value.masked_email) parts.push(peer.value.masked_email)
  return parts.join(' / ')
})

function goIdentity() {
  router.push('/settings/identity')
}

function dismissSession() {
  authStore.dismissLinkHint()
}

async function dismissForever() {
  try {
    await ElMessageBox.confirm(
      '选择"不再提示"后，30 天内系统不会再展示关联提示。是否继续？',
      '不再提示',
      { type: 'warning', confirmButtonText: '不再提示', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  dismissing.value = true
  try {
    await dismissIdentity()
    ElMessage.success('已设置不再提示，30 天后自动恢复')
    authStore.dismissLinkHint()
  } catch {
    // 拦截器已提示
  } finally {
    dismissing.value = false
  }
}

// 拉取对方主体脱敏信息（L3 最小披露，仅用于提示卡文案）
onMounted(async () => {
  if (!authStore.shouldShowLinkHint) return
  try {
    const res = await getLinkStatus()
    peer.value = res?.data?.peer || null
  } catch {
    // 拦截器已提示；失败不影响提示卡基础展示
  }
})
</script>

<style scoped lang="scss">
.link-hint-card {
  margin-bottom: 12px;
}

.hint-text {
  font-size: 13px;
}

.hint-actions {
  margin-left: 12px;
  white-space: nowrap;
}
</style>
