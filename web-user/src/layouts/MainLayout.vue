<template>
  <el-container class="main-layout">
    <el-header class="layout-header" height="56px">
      <div class="header-left">
        <img src="@/assets/logo.svg" alt="logo" class="logo" />
        <span class="product-name">{{ systemStore.productName }}</span>
      </div>
      <div class="header-right">
        <el-dropdown trigger="click" @command="handleCommand">
          <span class="user-entry">
            <el-icon class="avatar-icon"><UserFilled /></el-icon>
            <span class="nickname">{{ authStore.nickname || authStore.email }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>{{ authStore.email }}</el-dropdown-item>
              <el-dropdown-item divided command="identity">关联管理</el-dropdown-item>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-container class="layout-body">
      <el-aside class="layout-aside" width="208px">
        <el-menu
          :default-active="activeMenu"
          router
          class="aside-menu"
        >
          <el-menu-item
            v-for="item in menuItems"
            :key="item.path"
            :index="item.path"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-main class="layout-main">
        <LinkHintCard />
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useSystemStore } from '@/stores/system'
import LinkHintCard from '@/components/LinkHintCard.vue'

// T7 用户侧主布局：顶部导航 + 侧边菜单 + 内容区（不复用后台 MainLayout，A2 独立站点）
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const systemStore = useSystemStore()

// 菜单与 router/index.js children 保持一致
const menuItems = [
  { path: '/workflows', title: '我的工作流', icon: 'Share' },
  { path: '/kb', title: '知识库', icon: 'Collection' },
  { path: '/executions', title: '运行记录', icon: 'VideoPlay' },
  { path: '/quota', title: '配额看板', icon: 'Odometer' },
  { path: '/settings/identity', title: '关联管理', icon: 'Link' }
]

const activeMenu = computed(() => route.path)

async function handleCommand(command) {
  if (command === 'identity') {
    router.push('/settings/identity')
    return
  }
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定退出登录吗？', '提示', {
        confirmButtonText: '退出',
        cancelButtonText: '取消',
        type: 'warning'
      })
    } catch (e) {
      return
    }
    await authStore.logout()
    router.push('/login')
  }
}

onMounted(() => {
  systemStore.loadConfig()
  // 进入主布局后刷新客户信息快照（容错，不阻断）
  authStore.fetchCustomer()
})
</script>

<style scoped lang="scss">
.main-layout {
  height: 100vh;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--u-bg-header);
  border-bottom: 1px solid var(--u-border);
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;

  .logo {
    width: 28px;
    height: 28px;
  }

  .product-name {
    font-size: 16px;
    font-weight: 600;
  }
}

.user-entry {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--u-text-main);

  .avatar-icon {
    font-size: 20px;
    color: var(--u-text-sub);
  }
}

.layout-body {
  height: calc(100vh - var(--u-header-height));
}

.layout-aside {
  background: var(--u-bg-header);
  border-right: 1px solid var(--u-border);

  .aside-menu {
    border-right: none;
  }
}

.layout-main {
  background: var(--u-bg-page);
  padding: 16px 20px;
  overflow-y: auto;
}
</style>
