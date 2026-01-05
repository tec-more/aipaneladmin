<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #409EFF, #67C23A)">
            <el-icon :size="32"><User /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.userCount }}</div>
            <div class="stat-label">用户总数</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #E6A23C, #F56C6C)">
            <el-icon :size="32"><OfficeBuilding /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.deptCount }}</div>
            <div class="stat-label">部门总数</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #67C23A, #409EFF)">
            <el-icon :size="32"><Check /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.activeUsers }}</div>
            <div class="stat-label">活跃用户</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: linear-gradient(135deg, #909399, #606266)">
            <el-icon :size="32"><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ currentTime }}</div>
            <div class="stat-label">当前时间</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <span>欢迎使用</span>
          </template>
          <div class="welcome-content">
            <h2>AI Panel Admin 后台管理系统</h2>
            <p>欢迎回来，{{ userStore.username }}！</p>
            <el-divider />
            <h3>快速入口</h3>
            <div class="quick-links">
              <el-button type="primary" @click="$router.push('/users')">
                <el-icon><User /></el-icon>
                用户管理
              </el-button>
              <el-button type="success" @click="$router.push('/departments')">
                <el-icon><OfficeBuilding /></el-icon>
                部门管理
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span>个人信息</span>
          </template>
          <div class="user-profile">
            <el-avatar :size="80" :icon="UserFilled" />
            <div class="profile-info">
              <h3>{{ userStore.userInfo.username }}</h3>
              <p>{{ userStore.userInfo.email }}</p>
              <el-tag :type="userStore.isSuperuser ? 'danger' : 'info'" size="small">
                {{ userStore.isSuperuser ? '超级管理员' : '普通用户' }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { UserFilled } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const stats = ref({
  userCount: 0,
  deptCount: 0,
  activeUsers: 0
})

const currentTime = ref('')

let timer = null

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour12: false })
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)

  // 模拟数据
  stats.value = {
    userCount: 128,
    deptCount: 12,
    activeUsers: 86
  }
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<style lang="scss" scoped>
.dashboard {
  .stat-card {
    display: flex;
    align-items: center;
    padding: 20px;

    :deep(.el-card__body) {
      display: flex;
      align-items: center;
      width: 100%;
      padding: 0;
    }

    .stat-icon {
      width: 64px;
      height: 64px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      margin-right: 16px;
    }

    .stat-content {
      .stat-value {
        font-size: 24px;
        font-weight: bold;
        color: #333;
      }

      .stat-label {
        font-size: 14px;
        color: #999;
        margin-top: 4px;
      }
    }
  }

  .welcome-content {
    h2 {
      color: #333;
      margin-bottom: 8px;
    }

    p {
      color: #666;
    }

    h3 {
      color: #333;
      font-size: 16px;
      margin-bottom: 16px;
    }

    .quick-links {
      display: flex;
      gap: 12px;
    }
  }

  .user-profile {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;

    .profile-info {
      margin-top: 16px;

      h3 {
        font-size: 18px;
        color: #333;
        margin-bottom: 8px;
      }

      p {
        font-size: 14px;
        color: #999;
        margin-bottom: 12px;
      }
    }
  }
}
</style>
