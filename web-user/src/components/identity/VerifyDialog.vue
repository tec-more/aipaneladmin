<template>
  <!-- 身份关联验证弹窗（T14）：link/unlink 共用；L5 双通道 + L6 失败计数/锁定 -->
  <el-dialog
    v-model="visible"
    :title="mode === 'link' ? '关联账号验证' : '解除关联验证'"
    width="480px"
    :close-on-click-modal="false"
    @closed="onClosed"
  >
    <el-alert type="info" :closable="false" class="tip-alert">
      <template #title>
        <template v-if="mode === 'link'">
          关联仅用于身份识别，不共享工作流、知识库、额度与账单。需验证对方主体归属。
        </template>
        <template v-else>
          解除关联需再次验证对方主体归属。解绑后进入 30 天冷却期，期间不再提示关联。
        </template>
      </template>
    </el-alert>

    <!-- 对方主体脱敏信息（L3） -->
    <div v-if="peer" class="peer-card">
      <div class="peer-row">
        <span class="peer-label">对方主体</span>
        <el-tag size="small" effect="light">{{ peer.owner_type === 'usr' ? '后台账号' : '客户账号' }}</el-tag>
      </div>
      <div class="peer-row">
        <span class="peer-label">用户名</span>
        <span>{{ peer.username || '—' }}</span>
      </div>
      <div class="peer-row">
        <span class="peer-label">邮箱</span>
        <span>{{ peer.masked_email || '—' }}</span>
      </div>
    </div>

    <!-- 锁定提示（L6） -->
    <el-alert
      v-if="lockRemaining > 0"
      type="error"
      :closable="false"
      class="tip-alert"
    >
      验证失败次数过多，请 {{ lockRemaining }} 秒后重试
    </el-alert>

    <!-- 剩余尝试次数 -->
    <el-alert
      v-else-if="attemptsLeft !== null && attemptsLeft < 5"
      type="warning"
      :closable="false"
      class="tip-alert"
    >
      验证失败，剩余尝试次数 {{ attemptsLeft }} 次
    </el-alert>

    <el-form label-position="top" class="verify-form">
      <el-form-item label="验证方式">
        <el-radio-group v-model="verifyVia" :disabled="submitting || lockRemaining > 0">
          <el-radio value="email_code">邮箱验证码</el-radio>
          <el-radio value="password">对方主体密码</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item :label="verifyVia === 'email_code' ? '验证码' : '对方密码'">
        <div class="credential-row">
          <el-input
            v-model="credential"
            :type="verifyVia === 'password' ? 'password' : 'text'"
            :placeholder="verifyVia === 'email_code' ? '请输入发送至您邮箱的验证码' : '请输入对方主体登录密码'"
            :maxlength="verifyVia === 'email_code' ? 10 : 64"
            :disabled="submitting || lockRemaining > 0"
            show-password
            clearable
            @keyup.enter="onSubmit"
          />
          <el-button
            v-if="verifyVia === 'email_code'"
            :disabled="submitting || lockRemaining > 0 || codeCooldown > 0"
            :loading="sendingCode"
            @click="onSendCode"
          >
            {{ codeCooldown > 0 ? `${codeCooldown}s 后重发` : '发送验证码' }}
          </el-button>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button :disabled="submitting" @click="visible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        :disabled="!credential || lockRemaining > 0"
        @click="onSubmit"
      >
        {{ mode === 'link' ? '确认关联' : '确认解绑' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { linkIdentity, unlinkIdentity, sendLinkCode } from '@/api/identity'

/**
 * 身份关联/解绑验证弹窗（T14）
 * PRD §3.3：
 * - L5：cus→usr 用密码或邮箱验证码；usr→cus 用邮箱验证码（客户已设密码可改用密码）
 * - L6：失败 5 次锁定 10 分钟，前端展示剩余秒数
 * - 错误 data 通过 api/identity.js withBizData 透传到 err.bizData
 */
const emit = defineEmits(['success'])

const visible = ref(false)
const mode = ref('link') // 'link' | 'unlink'
const peer = ref(null)

const verifyVia = ref('email_code')
const credential = ref('')
const submitting = ref(false)

const sendingCode = ref(false)
const codeCooldown = ref(0)

const attemptsLeft = ref(null)
const lockRemaining = ref(0)

let cooldownTimer = null
let lockTimer = null

function open(m, peerInfo) {
  mode.value = m
  peer.value = peerInfo || null
  verifyVia.value = 'email_code'
  credential.value = ''
  attemptsLeft.value = null
  lockRemaining.value = 0
  visible.value = true
}

function clearTimers() {
  if (cooldownTimer) { clearInterval(cooldownTimer); cooldownTimer = null }
  if (lockTimer) { clearInterval(lockTimer); lockTimer = null }
}

function onClosed() {
  clearTimers()
  codeCooldown.value = 0
  sendingCode.value = false
}

async function onSendCode() {
  if (sendingCode.value || codeCooldown.value > 0) return
  sendingCode.value = true
  try {
    await sendLinkCode()
    ElMessage.success('验证码已发送，请查收邮箱')
    codeCooldown.value = 60
    cooldownTimer = setInterval(() => {
      codeCooldown.value -= 1
      if (codeCooldown.value <= 0) {
        clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    }, 1000)
  } catch {
    // 拦截器已提示（含 smtp_unavailable / send_code_rate_limited）
  } finally {
    sendingCode.value = false
  }
}

function startLockCountdown(seconds) {
  lockRemaining.value = seconds
  if (lockTimer) clearInterval(lockTimer)
  lockTimer = setInterval(() => {
    lockRemaining.value -= 1
    if (lockRemaining.value <= 0) {
      clearInterval(lockTimer)
      lockTimer = null
      attemptsLeft.value = null
    }
  }, 1000)
}

async function onSubmit() {
  if (submitting.value || !credential.value) return
  submitting.value = true
  attemptsLeft.value = null
  try {
    const payload = { verify_via: verifyVia.value, credential: credential.value }
    const api = mode.value === 'link' ? linkIdentity : unlinkIdentity
    const res = await api(payload)
    const data = res?.data ?? {}
    ElMessage.success(mode.value === 'link' ? '关联成功' : '已解除关联')
    visible.value = false
    emit('success', { mode: mode.value, data })
  } catch (err) {
    // 拦截器已 toast msg；读取 bizData 更新剩余次数 / 锁定倒计时
    const biz = err?.bizData || {}
    if (typeof biz.attempts_left === 'number') {
      attemptsLeft.value = biz.attempts_left
    }
    if (typeof biz.lock_remaining_seconds === 'number' && biz.lock_remaining_seconds > 0) {
      startLockCountdown(biz.lock_remaining_seconds)
      attemptsLeft.value = null
    }
  } finally {
    submitting.value = false
  }
}

onUnmounted(clearTimers)

defineExpose({ open })
</script>

<style scoped lang="scss">
.tip-alert {
  margin-bottom: 12px;
}

.peer-card {
  background: var(--u-bg-page);
  border: 1px solid var(--u-border);
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 12px;
}

.peer-row {
  display: flex;
  align-items: center;
  font-size: 13px;
  line-height: 22px;
}

.peer-label {
  width: 72px;
  color: var(--u-text-sub);
}

.verify-form {
  margin-top: 4px;
}

.credential-row {
  display: flex;
  gap: 8px;
  width: 100%;

  .el-input {
    flex: 1;
  }
}
</style>
