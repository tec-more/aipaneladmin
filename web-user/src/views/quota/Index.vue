<template>
  <!-- 配额看板（T14）+ 用量流水（T14+ K3） -->
  <div class="page-card">
    <div class="page-header">
      <h2 class="page-title">配额看板</h2>
      <el-button :icon="Refresh" :loading="loading" @click="onRefresh">刷新</el-button>
    </div>

    <el-tabs v-model="activeTab" class="quota-tabs">
      <!-- Tab1：配额看板 -->
      <el-tab-pane label="配额看板" name="board">
        <el-skeleton v-if="loading && !board" :rows="5" animated />

        <template v-else-if="board">
          <!-- 套餐概要 -->
          <el-card class="plan-card" shadow="never">
            <div class="plan-row">
              <div class="plan-item">
                <div class="plan-label">当前套餐</div>
                <div class="plan-value">
                  {{ board.plan_name || board.plan || '未绑定套餐' }}
                  <el-tag v-if="board.plan" size="small" effect="light" class="plan-code">{{ board.plan }}</el-tag>
                </div>
              </div>
              <div class="plan-item">
                <div class="plan-label">计费周期</div>
                <div class="plan-value">{{ board.period || '—' }}</div>
              </div>
              <div class="plan-item">
                <div class="plan-label">周期开始</div>
                <div class="plan-value">{{ formatTime(board.period_start) }}</div>
              </div>
              <div class="plan-item">
                <div class="plan-label">周期重置</div>
                <div class="plan-value">{{ formatTime(board.period_end) }}</div>
              </div>
            </div>
          </el-card>

          <!-- 配额项列表 -->
          <el-card class="items-card" shadow="never">
            <template #header>
              <span class="card-title">配额项</span>
            </template>

            <el-empty v-if="!board.plan" description="未绑定套餐，暂无配额项" />
            <el-empty v-else-if="!items.length" description="套餐未定义配额项" />

            <div v-else class="quota-list">
              <div v-for="it in items" :key="it.item" class="quota-row">
                <div class="quota-head">
                  <span class="quota-name">{{ itemLabel(it.item) }}</span>
                  <span class="quota-code">{{ it.item }}</span>
                </div>

                <!-- 并发项特殊展示：当前占用/上限 -->
                <div v-if="it.item === 'concurrency'" class="quota-conc">
                  <el-tag :type="concTagType(it)" effect="light">
                    当前占用 {{ fmtNum(it.used) }} / 上限 {{ fmtNum(it.limit) }}
                  </el-tag>
                  <span class="quota-tip">运行中实例数，超限将被拒绝</span>
                </div>

                <!-- 常规配额项：进度条 -->
                <template v-else>
                  <el-progress
                    :percentage="usagePercent(it)"
                    :color="progressColor(it)"
                    :stroke-width="14"
                    :format="() => ''"
                  />
                  <div class="quota-meta">
                    <span>已用 {{ fmtNum(it.used) }}</span>
                    <span v-if="it.held > 0" class="quota-held">预占 {{ fmtNum(it.held) }}</span>
                    <span>上限 {{ fmtNum(it.limit) }}</span>
                    <span class="quota-remain">剩余 {{ fmtNum(remaining(it)) }}</span>
                  </div>
                </template>
              </div>
            </div>
          </el-card>
        </template>

        <el-empty v-else description="看板加载失败" />
      </el-tab-pane>

      <!-- Tab2：用量流水（T14+ K3） -->
      <el-tab-pane label="用量流水" name="usage">
        <el-card shadow="never" class="usage-card">
          <div class="usage-filters">
            <el-input
              v-model="usageQuery.execution_id"
              placeholder="执行实例 ID"
              clearable
              style="width: 160px"
              @keyup.enter="loadUsage(1)"
              @clear="loadUsage(1)"
            />
            <el-input
              v-model="usageQuery.resource_type"
              placeholder="资源类型（如 llm_token）"
              clearable
              style="width: 200px"
              @keyup.enter="loadUsage(1)"
              @clear="loadUsage(1)"
            />
            <el-button type="primary" @click="loadUsage(1)">查询</el-button>
          </div>

          <el-table v-loading="usageLoading" :data="usageList" class="usage-table">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="execution_id" label="执行实例" width="100">
              <template #default="{ row }">{{ row.execution_id ?? '—' }}</template>
            </el-table-column>
            <el-table-column prop="node_id" label="节点" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.node_id || '—' }}</template>
            </el-table-column>
            <el-table-column prop="resource_type" label="资源类型" width="140">
              <template #default="{ row }">
                <el-tag size="small" effect="light">{{ row.resource_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="用量" width="100" align="right">
              <template #default="{ row }">{{ fmtNum(row.amount) }}</template>
            </el-table-column>
            <el-table-column label="Token (入/出)" width="140" align="right">
              <template #default="{ row }">
                {{ fmtNum(row.tokens_in) }} / {{ fmtNum(row.tokens_out) }}
              </template>
            </el-table-column>
            <el-table-column label="成本" width="110" align="right">
              <template #default="{ row }">{{ fmtCost(row.cost) }}</template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="170">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <template #empty>
              <el-empty description="暂无用量流水" />
            </template>
          </el-table>

          <el-pagination
            v-model:current-page="usageQuery.page"
            :page-size="usageQuery.page_size"
            :total="usageTotal"
            layout="total, prev, pager, next"
            class="usage-pagination"
            @current-change="loadUsage()"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { getQuotaBoard, getUsageRecords } from '@/api/quota'

/**
 * 配额看板（T14）+ 用量流水（T14+ K3）
 * 溯源：docs/arch/04 §2.3 GET /v1/u/quota 返回 {plan, period, items[limit/used/held]}；
 * PRD §7.3：用户可见剩余额度、重置时间、本次消耗。
 * Q3-A：阈值固定 80%（used+held）/limit ≥ 0.8 橙色，≥1.0 红色。
 * T14+ K3：用量流水归属过滤由服务端强制，前端不传 owner_*。
 */
const loading = ref(false)
const board = ref(null)
const activeTab = ref('board')

const items = computed(() => (board.value?.items || []).slice())

const ITEM_LABELS = {
  token: '模型 Token',
  llm_token: '模型 Token',
  concurrency: '并发运行数',
  daily_runs: '每日运行数',
  kb_search: '知识库检索',
  vector_write: '向量写入',
  tool_call: '工具调用',
  run_budget: '单次运行预算'
}

function itemLabel(code) {
  return ITEM_LABELS[code] || code
}

function fmtNum(n) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  if (Math.abs(v) >= 10000) return v.toLocaleString('zh-CN')
  return Number.isInteger(v) ? String(v) : v.toFixed(2)
}

function usageRate(it) {
  const limit = Number(it.limit) || 0
  if (limit <= 0) return 0
  const used = (Number(it.used) || 0) + (Number(it.held) || 0)
  return used / limit
}

function usagePercent(it) {
  return Math.min(Math.round(usageRate(it) * 100), 100)
}

function remaining(it) {
  const limit = Number(it.limit) || 0
  const used = (Number(it.used) || 0) + (Number(it.held) || 0)
  return Math.max(limit - used, 0)
}

function progressColor(it) {
  const rate = usageRate(it)
  if (rate >= 1) return '#f56c6c'
  if (rate >= 0.8) return '#e6a23c'
  return 'var(--u-primary)'
}

function concTagType(it) {
  const limit = Number(it.limit) || 0
  const used = Number(it.used) || 0
  if (limit <= 0) return 'info'
  if (used >= limit) return 'danger'
  if (used / limit >= 0.8) return 'warning'
  return 'success'
}

function formatTime(t) {
  return t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '—'
}

async function loadBoard() {
  loading.value = true
  try {
    const res = await getQuotaBoard()
    board.value = res?.data ?? null
  } catch {
    // 拦截器已提示
    board.value = null
  } finally {
    loading.value = false
  }
}

// ============ 用量流水（T14+ K3） ============
const usageLoading = ref(false)
const usageList = ref([])
const usageTotal = ref(0)
const usageQuery = ref({
  page: 1,
  page_size: 20,
  execution_id: '',
  resource_type: ''
})

async function loadUsage(resetPage) {
  if (resetPage) usageQuery.value.page = 1
  usageLoading.value = true
  try {
    const params = {
      page: usageQuery.value.page,
      page_size: usageQuery.value.page_size
    }
    // execution_id 必须是正整数
    const eid = String(usageQuery.value.execution_id || '').trim()
    if (eid) {
      const n = Number(eid)
      if (Number.isInteger(n) && n > 0) params.execution_id = n
    }
    const rt = String(usageQuery.value.resource_type || '').trim()
    if (rt) params.resource_type = rt
    const res = await getUsageRecords(params)
    usageList.value = res?.data?.items || []
    usageTotal.value = res?.data?.total || 0
  } catch {
    // 拦截器已提示
    usageList.value = []
    usageTotal.value = 0
  } finally {
    usageLoading.value = false
  }
}

function fmtCost(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return n.toFixed(6)
}

function onRefresh() {
  if (activeTab.value === 'usage') loadUsage()
  else loadBoard()
}

onMounted(() => {
  loadBoard()
  loadUsage()
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

.plan-card {
  margin-bottom: 16px;
  border: 1px solid var(--u-border);
}

.plan-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.plan-label {
  font-size: 12px;
  color: var(--u-text-sub);
  margin-bottom: 6px;
}

.plan-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--u-text-main);
}

.plan-code {
  margin-left: 8px;
  font-weight: 400;
}

.items-card {
  border: 1px solid var(--u-border);
}

.card-title {
  font-size: 14px;
  font-weight: 600;
}

.quota-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.quota-row {
  padding: 4px 0 12px;
  border-bottom: 1px dashed var(--u-border);

  &:last-child {
    border-bottom: none;
  }
}

.quota-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 8px;
}

.quota-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--u-text-main);
}

.quota-code {
  font-size: 12px;
  color: var(--u-text-sub);
  font-family: Menlo, Consolas, monospace;
}

.quota-meta {
  display: flex;
  gap: 16px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--u-text-sub);
}

.quota-held {
  color: #e6a23c;
}

.quota-remain {
  margin-left: auto;
  font-weight: 600;
  color: var(--u-text-main);
}

.quota-conc {
  display: flex;
  align-items: center;
  gap: 12px;
}

.quota-tip {
  font-size: 12px;
  color: var(--u-text-sub);
}

/* T14+ K3 用量流水 */
.quota-tabs {
  margin-top: 4px;
}

.usage-card {
  border: 1px solid var(--u-border);
}

.usage-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.usage-table {
  margin-bottom: 12px;
}

.usage-pagination {
  display: flex;
  justify-content: flex-end;
}
</style>
