<template>
  <div class="report-index">
    <el-card shadow="never" class="search-card">
      <div class="card-header">
        <span>财务报表</span>
      </div>
      
      <div class="report-tabs">
        <el-button 
          v-for="tab in tabs" 
          :key="tab.key"
          :type="activeTab === tab.key ? 'primary' : 'default'"
          @click="activeTab = tab.key"
        >{{ tab.label }}</el-button>
      </div>
      
      <div class="report-filters">
        <el-form :inline="true" :model="filterForm" class="filter-form">
          <el-form-item label="年份">
            <el-select v-model="filterForm.year" style="width: 100px">
              <el-option v-for="year in years" :key="year" :value="year">{{ year }}年</el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="月份">
            <el-select v-model="filterForm.month" style="width: 100px">
              <el-option v-for="month in months" :key="month" :value="month">{{ month }}月</el-option>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="generateReport">生成报表</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    
    <el-card shadow="never" class="table-card">
      <template #header>
        <span>{{ currentTabLabel }}</span>
      </template>
      
      <el-table v-if="activeTab === 'trial_balance'" :data="trialBalanceData" border stripe>
        <el-table-column prop="account_code" label="科目编码" />
        <el-table-column prop="account_name" label="科目名称" />
        <el-table-column prop="account_type" label="科目类型" />
        <el-table-column prop="opening_debit" label="期初借方" />
        <el-table-column prop="opening_credit" label="期初贷方" />
        <el-table-column prop="period_debit" label="本期借方" />
        <el-table-column prop="period_credit" label="本期贷方" />
        <el-table-column prop="ending_debit" label="期末借方" />
        <el-table-column prop="ending_credit" label="期末贷方" />
      </el-table>
      
      <div v-if="activeTab === 'profit_loss'" class="profit-loss-container">
        <div class="section">
          <h4>一、营业收入</h4>
          <div v-for="item in profitLossData.revenue_items" :key="item.name" class="item-row">
            <span>{{ item.name }}</span>
            <span>{{ item.amount }}</span>
          </div>
          <div class="total-row">
            <span>营业收入合计</span>
            <span>{{ profitLossData.total_revenue }}</span>
          </div>
        </div>
        
        <div class="section">
          <h4>二、营业成本</h4>
          <div v-for="item in profitLossData.cost_items" :key="item.name" class="item-row">
            <span>{{ item.name }}</span>
            <span>{{ item.amount }}</span>
          </div>
          <div class="total-row">
            <span>营业成本合计</span>
            <span>{{ profitLossData.total_cost }}</span>
          </div>
        </div>
        
        <div class="section">
          <h4>三、营业利润</h4>
          <div class="item-row">
            <span>营业利润</span>
            <span>{{ profitLossData.operating_profit }}</span>
          </div>
        </div>
        
        <div class="section">
          <h4>四、利润总额</h4>
          <div class="item-row">
            <span>利润总额</span>
            <span>{{ profitLossData.total_profit }}</span>
          </div>
        </div>
        
        <div class="section">
          <h4>五、净利润</h4>
          <div class="item-row">
            <span>净利润</span>
            <span>{{ profitLossData.net_profit }}</span>
          </div>
        </div>
      </div>
      
      <div v-if="activeTab === 'balance_sheet'" class="balance-sheet-container">
        <div class="left-section">
          <h4>资产</h4>
          <div class="section">
            <h5>流动资产</h5>
            <div v-for="item in balanceSheetData.current_assets" :key="item.name" class="item-row">
              <span>{{ item.name }}</span>
              <span>{{ item.amount }}</span>
            </div>
            <div class="total-row">
              <span>流动资产合计</span>
              <span>{{ balanceSheetData.total_current_assets }}</span>
            </div>
          </div>
          <div class="section">
            <h5>非流动资产</h5>
            <div v-for="item in balanceSheetData.non_current_assets" :key="item.name" class="item-row">
              <span>{{ item.name }}</span>
              <span>{{ item.amount }}</span>
            </div>
            <div class="total-row">
              <span>非流动资产合计</span>
              <span>{{ balanceSheetData.total_non_current_assets }}</span>
            </div>
          </div>
          <div class="grand-total">
            <span>资产总计</span>
            <span>{{ balanceSheetData.total_assets }}</span>
          </div>
        </div>
        
        <div class="right-section">
          <h4>负债和所有者权益</h4>
          <div class="section">
            <h5>流动负债</h5>
            <div v-for="item in balanceSheetData.current_liabilities" :key="item.name" class="item-row">
              <span>{{ item.name }}</span>
              <span>{{ item.amount }}</span>
            </div>
            <div class="total-row">
              <span>流动负债合计</span>
              <span>{{ balanceSheetData.total_current_liabilities }}</span>
            </div>
          </div>
          <div class="section">
            <h5>非流动负债</h5>
            <div v-for="item in balanceSheetData.non_current_liabilities" :key="item.name" class="item-row">
              <span>{{ item.name }}</span>
              <span>{{ item.amount }}</span>
            </div>
            <div class="total-row">
              <span>非流动负债合计</span>
              <span>{{ balanceSheetData.total_non_current_liabilities }}</span>
            </div>
          </div>
          <div class="section">
            <h5>所有者权益</h5>
            <div v-for="item in balanceSheetData.equity" :key="item.name" class="item-row">
              <span>{{ item.name }}</span>
              <span>{{ item.amount }}</span>
            </div>
            <div class="total-row">
              <span>所有者权益合计</span>
              <span>{{ balanceSheetData.total_equity }}</span>
            </div>
          </div>
          <div class="grand-total">
            <span>负债和所有者权益总计</span>
            <span>{{ balanceSheetData.total_liabilities_equity }}</span>
          </div>
        </div>
      </div>
      
      <div v-if="activeTab === 'cash_flow'" class="cash-flow-container">
        <div class="summary-row">
          <span>期初现金余额</span>
          <span>{{ cashFlowData.cash_beginning_balance }}</span>
        </div>
        
        <div class="section">
          <h4>一、经营活动产生的现金流量</h4>
          <div class="section-row">
            <span>现金流入</span>
            <span>{{ cashFlowData.operating.cash_inflow }}</span>
          </div>
          <div class="section-row">
            <span>现金流出</span>
            <span>{{ cashFlowData.operating.cash_outflow }}</span>
          </div>
          <div class="net-row">
            <span>经营活动净现金流</span>
            <span>{{ cashFlowData.operating.net_cash_flow }}</span>
          </div>
        </div>
        
        <div class="section">
          <h4>二、投资活动产生的现金流量</h4>
          <div class="section-row">
            <span>现金流入</span>
            <span>{{ cashFlowData.investing.cash_inflow }}</span>
          </div>
          <div class="section-row">
            <span>现金流出</span>
            <span>{{ cashFlowData.investing.cash_outflow }}</span>
          </div>
          <div class="net-row">
            <span>投资活动净现金流</span>
            <span>{{ cashFlowData.investing.net_cash_flow }}</span>
          </div>
        </div>
        
        <div class="section">
          <h4>三、筹资活动产生的现金流量</h4>
          <div class="section-row">
            <span>现金流入</span>
            <span>{{ cashFlowData.financing.cash_inflow }}</span>
          </div>
          <div class="section-row">
            <span>现金流出</span>
            <span>{{ cashFlowData.financing.cash_outflow }}</span>
          </div>
          <div class="net-row">
            <span>筹资活动净现金流</span>
            <span>{{ cashFlowData.financing.net_cash_flow }}</span>
          </div>
        </div>
        
        <div class="section">
          <h4>四、现金净增加额</h4>
          <div class="grand-total">
            <span>现金净增加额</span>
            <span>{{ cashFlowData.net_cash_flow }}</span>
          </div>
        </div>
        
        <div class="section">
          <h4>五、期末现金余额</h4>
          <div class="grand-total">
            <span>期末现金余额</span>
            <span>{{ cashFlowData.cash_ending_balance }}</span>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'

const tabs = [
  { key: 'trial_balance', label: '科目余额表' },
  { key: 'profit_loss', label: '利润表' },
  { key: 'balance_sheet', label: '资产负债表' },
  { key: 'cash_flow', label: '现金流量表' }
]

const activeTab = ref('trial_balance')
const currentTabLabel = computed(() => {
  const tab = tabs.find(t => t.key === activeTab.value)
  return tab ? tab.label : ''
})

const filterForm = reactive({
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1
})

const years = []
const months = []
for (let i = 2020; i <= new Date().getFullYear() + 1; i++) {
  years.push(i)
}
for (let i = 1; i <= 12; i++) {
  months.push(i)
}

const trialBalanceData = ref([])
const profitLossData = ref({
  revenue_items: [],
  cost_items: [],
  total_revenue: 0,
  total_cost: 0,
  operating_profit: 0,
  total_profit: 0,
  net_profit: 0
})
const balanceSheetData = ref({
  current_assets: [],
  non_current_assets: [],
  total_current_assets: 0,
  total_non_current_assets: 0,
  total_assets: 0,
  current_liabilities: [],
  non_current_liabilities: [],
  total_current_liabilities: 0,
  total_non_current_liabilities: 0,
  equity: [],
  total_equity: 0,
  total_liabilities_equity: 0
})

const cashFlowData = ref({
  cash_beginning_balance: 0,
  cash_ending_balance: 0,
  net_cash_flow: 0,
  operating: {
    cash_inflow: 0,
    cash_outflow: 0,
    net_cash_flow: 0,
    items: []
  },
  investing: {
    cash_inflow: 0,
    cash_outflow: 0,
    net_cash_flow: 0,
    items: []
  },
  financing: {
    cash_inflow: 0,
    cash_outflow: 0,
    net_cash_flow: 0,
    items: []
  }
})

const generateReport = async () => {
  const response = await fetch(
    `/api/finance/reports/${activeTab.value}?year=${filterForm.year}&month=${filterForm.month}`
  )
  const data = await response.json()
  
  if (data.code === 0 || response.ok) {
    if (activeTab.value === 'trial_balance') {
      trialBalanceData.value = data.data || []
    } else if (activeTab.value === 'profit_loss') {
      profitLossData.value = data.data || data
    } else if (activeTab.value === 'balance_sheet') {
      balanceSheetData.value = data.data || data
    } else if (activeTab.value === 'cash_flow') {
      cashFlowData.value = data.data || data
    }
  } else {
    alert(data.msg || '生成报表失败')
  }
}

onMounted(() => {
  generateReport()
})
</script>

<style lang="scss" scoped>
.report-index {
  padding: 20px;
  
  .report-tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
  }
  
  .report-filters {
    margin-bottom: 20px;
  }
  
  .profit-loss-container, .balance-sheet-container, .cash-flow-container {
    .section {
      margin-bottom: 20px;
      
      h4, h5 {
        margin: 0 0 10px 0;
        padding-bottom: 5px;
        border-bottom: 1px solid #eee;
      }
      
      .item-row, .section-row {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
      }
      
      .total-row, .net-row {
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        font-weight: bold;
        border-top: 1px solid #eee;
        margin-top: 5px;
      }
      
      .grand-total {
        display: flex;
        justify-content: space-between;
        padding: 15px 0;
        font-weight: bold;
        font-size: 1.2em;
        border-top: 2px solid #333;
        margin-top: 10px;
      }
    }
  }
  
  .balance-sheet-container {
    display: flex;
    gap: 40px;
    
    .left-section, .right-section {
      flex: 1;
    }
  }
  
  .cash-flow-container {
    .summary-row {
      display: flex;
      justify-content: space-between;
      padding: 10px 0;
      font-weight: bold;
      font-size: 1.1em;
      border-bottom: 2px solid #333;
      margin-bottom: 20px;
    }
  }
}
</style>