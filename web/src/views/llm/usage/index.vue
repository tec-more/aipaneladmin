<template>
  <div class="usage-stats">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #409eff">
              <el-icon :size="24"><ChatLineRound /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ statistics.total_records || 0 }}</div>
              <div class="stat-label">总请求数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #67c23a">
              <el-icon :size="24"><Tickets /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ formatNumber(statistics.total_tokens || 0) }}</div>
              <div class="stat-label">总Token数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #e6a23c">
              <el-icon :size="24"><Coin /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">¥{{ statistics.total_cost?.toFixed(2) || '0.00' }}</div>
              <div class="stat-label">总成本</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #f56c6c">
              <el-icon :size="24"><TrendCharts /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ formatNumber(statistics.average_tokens_per_request || 0) }}</div>
              <div class="stat-label">平均Token/请求</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>每日使用趋势</span>
              <el-select v-model="dailyDays" @change="fetchDailyStats" style="width: 120px">
                <el-option label="最近7天" :value="7" />
                <el-option label="最近14天" :value="14" />
                <el-option label="最近30天" :value="30" />
              </el-select>
            </div>
          </template>
          <div ref="dailyChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>
            <span>模型使用分布</span>
          </template>
          <div ref="modelChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 使用记录 -->
    <el-card shadow="never" class="mt-20">
      <template #header>
        <div class="card-header">
          <span>使用记录</span>
          <div>
            <el-select v-model="searchForm.customer_id" placeholder="客户ID" clearable filterable style="width: 150px; margin-right: 10px">
              <el-option v-for="item in customerTopList" :key="item.customer_id" :label="`客户${item.customer_id}`" :value="item.customer_id" />
            </el-select>
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              @change="handleDateChange"
              style="margin-right: 10px"
            />
            <el-button type="primary" :icon="Search" @click="fetchRecords">搜索</el-button>
            <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="recordsLoading" :data="recordsList" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="conversation_id" label="对话ID" min-width="150" show-overflow-tooltip />
        <el-table-column prop="model_id" label="模型ID" width="100" align="center" />
        <el-table-column prop="customer_id" label="客户ID" width="100" align="center" />
        <el-table-column label="Token统计" width="200" align="center">
          <template #default="{ row }">
            <div>输入: {{ formatNumber(row.prompt_tokens) }}</div>
            <div>输出: {{ formatNumber(row.completion_tokens) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="total_tokens" label="总计" width="100" align="center">
          <template #default="{ row }">
            {{ formatNumber(row.total_tokens) }}
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="成本(元)" width="120" align="center">
          <template #default="{ row }">
            ¥{{ row.cost?.toFixed(4) || '0.0000' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="180" />
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="recordsPagination.page"
          v-model:page-size="recordsPagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="recordsPagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchRecords"
          @current-change="fetchRecords"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { Search, Refresh, ChatLineRound, Tickets, Coin, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  getUsageStatistics,
  getDailyStatistics,
  getModelStatistics,
  getCustomerStatistics,
  getUsageRecords
} from '@/api/llm'

let dailyChart = null
let modelChart = null

const dailyChartRef = ref()
const modelChartRef = ref()
const dailyDays = ref(7)
const dateRange = ref([])
const recordsLoading = ref(false)

const statistics = ref({})
const dailyStats = ref([])
const modelStats = ref([])
const customerTopList = ref([])
const recordsList = ref([])

const searchForm = reactive({
  customer_id: null,
  start_date: null,
  end_date: null
})

const recordsPagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const fetchStatistics = async () => {
  try {
    const { data } = await getUsageStatistics({ days: 7 })
    statistics.value = data
  } catch (error) {
    ElMessage.error('获取统计数据失败')
  }
}

const fetchDailyStats = async () => {
  try {
    const { data } = await getDailyStatistics({ days: dailyDays.value })
    dailyStats.value = data.daily_stats || []
    renderDailyChart()
  } catch (error) {
    ElMessage.error('获取每日统计失败')
  }
}

const fetchModelStats = async () => {
  try {
    const { data } = await getModelStatistics()
    modelStats.value = data.model_stats || []
    renderModelChart()
  } catch (error) {
    ElMessage.error('获取模型统计失败')
  }
}

const fetchCustomerStats = async () => {
  try {
    const { data } = await getCustomerStatistics({ top_n: 20 })
    customerTopList.value = data.customer_stats || []
  } catch (error) {
    console.error('获取客户统计失败', error)
  }
}

const fetchRecords = async () => {
  recordsLoading.value = true
  try {
    const { data } = await getUsageRecords({
      ...searchForm,
      page: recordsPagination.page,
      page_size: recordsPagination.pageSize
    })
    recordsList.value = data.items || []
    recordsPagination.total = data.total || 0
  } catch (error) {
    ElMessage.error('获取使用记录失败')
  } finally {
    recordsLoading.value = false
  }
}

const handleDateChange = (dates) => {
  if (dates && dates.length === 2) {
    searchForm.start_date = dates[0]
    searchForm.end_date = dates[1]
  } else {
    searchForm.start_date = null
    searchForm.end_date = null
  }
}

const handleReset = () => {
  searchForm.customer_id = null
  searchForm.start_date = null
  searchForm.end_date = null
  dateRange.value = []
  fetchRecords()
}

const renderDailyChart = () => {
  if (!dailyChartRef.value) return

  if (!dailyChart) {
    dailyChart = echarts.init(dailyChartRef.value)
  }

  const dates = dailyStats.value.map(item => item.date)
  const tokens = dailyStats.value.map(item => item.total_tokens)
  const costs = dailyStats.value.map(item => item.total_cost)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['Token数', '成本(元)']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: [
      {
        type: 'value',
        name: 'Token数',
        position: 'left'
      },
      {
        type: 'value',
        name: '成本(元)',
        position: 'right'
      }
    ],
    series: [
      {
        name: 'Token数',
        type: 'line',
        data: tokens,
        smooth: true,
        itemStyle: { color: '#409eff' }
      },
      {
        name: '成本(元)',
        type: 'line',
        yAxisIndex: 1,
        data: costs,
        smooth: true,
        itemStyle: { color: '#67c23a' }
      }
    ]
  }

  dailyChart.setOption(option)
}

const renderModelChart = () => {
  if (!modelChartRef.value) return

  if (!modelChart) {
    modelChart = echarts.init(modelChartRef.value)
  }

  const modelNames = modelStats.value.map(item => `模型${item.model_id}`)
  const tokenData = modelStats.value.map(item => ({
    value: item.total_tokens,
    name: `模型${item.model_id}`
  }))

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} tokens ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        type: 'pie',
        radius: '50%',
        data: tokenData,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }

  modelChart.setOption(option)
}

const formatNumber = (num) => {
  if (!num) return '0'
  return num.toLocaleString()
}

const handleResize = () => {
  dailyChart?.resize()
  modelChart?.resize()
}

onMounted(async () => {
  await fetchStatistics()
  await fetchDailyStats()
  await fetchModelStats()
  await fetchCustomerStats()
  await fetchRecords()

  await nextTick()
  renderDailyChart()
  renderModelChart()

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  dailyChart?.dispose()
  modelChart?.dispose()
})
</script>

<style scoped>
.usage-stats {
  padding: 20px;
}

.stats-cards {
  margin-bottom: 20px;
}

.stat-card {
  height: 100px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.charts-row {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.mt-20 {
  margin-top: 20px;
}
</style>
