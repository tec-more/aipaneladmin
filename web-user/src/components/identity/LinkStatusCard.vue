<template>
  <!-- 身份关联状态卡（T14）：5 态渲染 + 操作入口 -->
  <el-card class="status-card" shadow="never">
    <div class="status-header">
      <div class="status-title-row">
        <el-icon class="status-icon" :class="iconClass"><component :is="icon" /></el-icon>
        <div>
          <div class="status-title">{{ title }}</div>
          <div class="status-sub">{{ subtitle }}</div>
        </div>
      </div>
      <el-tag :type="tagType" effect="light">{{ tagText }}</el-tag>
    </div>

    <!-- 对方主体脱敏信息（L3：不展示资产数据） -->
    <div v-if="peer" class="peer-block">
      <div class="peer-row">
        <span class="peer-label">对方主体类型</span>
        <span>{{ peer.owner_type === 'usr' ? '后台账号' : '客户账号' }}</span>
      </div>
      <div class="peer-row">
        <span class="peer-label">用户名</span>
        <span>{{ peer.username || '—' }}</span>
      </div>
      <div class="peer-row">
        <span class="peer-label">邮箱</span>
        <span>{{ peer.masked_email || '—' }}</span>
      </div>
      <div v-if="linkedAt" class="peer-row">
        <span class="peer-label">关联时间</span>
        <span>{{ formatTime(linkedAt) }}</span>
      </div>
      <div v-if="dismissedUntil" class="peer-row">
        <span class="peer-label">{{ status === 'cooldown' ? '冷却截止' : '自动恢复提示' }}</span>
        <span>{{ formatTime(dismissedUntil) }}</span>
      </div>
    </div>

    <!-- 操作区 -->
    <div v-if="hasActions" class="actions">
      <el-button v-if="status === 'prompted'" type="primary" @click="$emit('link')">
        立即关联
      </el-button>
      <el-button v-if="status === 'prompted'" @click="$emit('dismiss')">
        不再提示（30 天）
      </el-button>
      <el-button v-if="status === 'linked'" type="danger" plain @click="$emit('unlink')">
        解除关联
      </el-button>
      <el-button v-if="status === 'dismissed'" type="primary" plain @click="$emit('resume')">
        重新开启提示
      </el-button>
    </div>

    <!-- 状态说明 -->
    <el-alert v-if="notice" :type="noticeType" :closable="false" class="notice">
      {{ notice }}
    </el-alert>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { CircleCheck, InfoFilled, Link, Lock, Timer } from '@element-plus/icons-vue'

/**
 * 身份关联状态卡（T14）
 * PRD §3.3 状态机：none / prompted / linked / dismissed / cooldown
 * 操作：
 * - prompted → 立即关联 / 不再提示
 * - linked → 解除关联
 * - dismissed/cooldown → 仅文案（Q2-A：30 天自动恢复，无手动按钮）
 * - none → 无操作
 */
const props = defineProps({
  status: { type: String, required: true },
  peer: { type: Object, default: null },
  linkedAt: { type: String, default: null },
  dismissedUntil: { type: String, default: null },
  reasonMessage: { type: String, default: '' }
})

defineEmits(['link', 'unlink', 'dismiss', 'resume'])

const META = {
  none: {
    title: '未检测到可关联账号',
    subtitle: '当前邮箱未匹配到其他主体',
    tag: '未关联',
    tagType: 'info',
    icon: InfoFilled,
    iconClass: 'is-info'
  },
  prompted: {
    title: '发现可关联账号',
    subtitle: '确认是否关联到同一自然人',
    tag: '待确认',
    tagType: 'warning',
    icon: Link,
    iconClass: 'is-warning'
  },
  linked: {
    title: '已关联',
    subtitle: '仅建立身份映射，资产互不共享',
    tag: '已关联',
    tagType: 'success',
    icon: CircleCheck,
    iconClass: 'is-success'
  },
  dismissed: {
    title: '已设置不再提示',
    subtitle: '30 天后自动恢复关联提示',
    tag: '已关闭提示',
    tagType: 'info',
    icon: Lock,
    iconClass: 'is-info'
  },
  cooldown: {
    title: '解绑冷却中',
    subtitle: '冷却期内不再提示，期满后恢复',
    tag: '冷却中',
    tagType: 'info',
    icon: Timer,
    iconClass: 'is-info'
  }
}

const meta = computed(() => META[props.status] || META.none)
const title = computed(() => meta.value.title)
const subtitle = computed(() => meta.value.subtitle)
const tagText = computed(() => meta.value.tag)
const tagType = computed(() => meta.value.tagType)
const icon = computed(() => meta.value.icon)
const iconClass = computed(() => meta.value.iconClass)

const hasActions = computed(() => ['prompted', 'linked', 'dismissed'].includes(props.status))

const notice = computed(() => {
  if (props.status === 'linked') {
    return '关联仅用于身份识别，不共享工作流、知识库、额度与账单。'
  }
  if (props.status === 'dismissed') {
    return '您已选择不再提示关联，30 天后系统将自动恢复提示。'
  }
  if (props.status === 'cooldown') {
    return '解除关联后进入 30 天冷却期，期间不再提示关联，期满后自动恢复。'
  }
  if (props.status === 'none' && props.reasonMessage) {
    return props.reasonMessage
  }
  return ''
})
const noticeType = computed(() => (props.status === 'linked' ? 'success' : 'info'))

function formatTime(t) {
  return t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '—'
}
</script>

<style scoped lang="scss">
.status-card {
  border: 1px solid var(--u-border);
}

.status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.status-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-icon {
  font-size: 28px;

  &.is-success { color: #67c23a; }
  &.is-warning { color: #e6a23c; }
  &.is-info { color: var(--u-text-sub); }
}

.status-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--u-text-main);
}

.status-sub {
  font-size: 12px;
  color: var(--u-text-sub);
  margin-top: 2px;
}

.peer-block {
  background: var(--u-bg-page);
  border: 1px solid var(--u-border);
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 12px;
}

.peer-row {
  display: flex;
  font-size: 13px;
  line-height: 24px;
}

.peer-label {
  width: 96px;
  color: var(--u-text-sub);
}

.actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.notice {
  margin-top: 4px;
}
</style>
