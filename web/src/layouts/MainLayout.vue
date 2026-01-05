<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <img src="@/assets/logo.svg" alt="logo" class="logo-img" />
        <span v-show="!isCollapse" class="logo-text">AI Panel</span>
      </div>

      <el-menu
        :default-active="currentRoute"
        :collapse="isCollapse"
        :collapse-transition="false"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        router
      >
        <!-- 动态菜单渲染 -->
        <template v-for="menu in menuStore.menuTree" :key="menu.id">
          <!-- 有子菜单的情况 -->
          <el-sub-menu v-if="menu.children && menu.children.length > 0" :index="menu.path || `menu-${menu.id}`">
            <template #title>
              <el-icon>
                <component :is="getIconComponent(menu.icon)" />
              </el-icon>
              <span>{{ menu.name }}</span>
            </template>
            <!-- 递归渲染子菜单 -->
            <template v-for="child in menu.children" :key="child.id">
              <el-sub-menu v-if="child.children && child.children.length > 0" :index="child.path || `menu-${child.id}`">
                <template #title>
                  <el-icon>
                    <component :is="getIconComponent(child.icon)" />
                  </el-icon>
                  <span>{{ child.name }}</span>
                </template>
                <el-menu-item v-for="subChild in child.children" :key="subChild.id" :index="subChild.path">
                  <el-icon>
                    <component :is="getIconComponent(subChild.icon)" />
                  </el-icon>
                  <template #title>{{ subChild.name }}</template>
                </el-menu-item>
              </el-sub-menu>
              <el-menu-item v-else :index="child.path">
                <el-icon>
                  <component :is="getIconComponent(child.icon)" />
                </el-icon>
                <template #title>{{ child.name }}</template>
              </el-menu-item>
            </template>
          </el-sub-menu>
          <!-- 没有子菜单的情况 -->
          <el-menu-item v-else :index="menu.path">
            <el-icon>
              <component :is="getIconComponent(menu.icon)" />
            </el-icon>
            <template #title>{{ menu.name }}</template>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="toggleCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentMeta.title">
              {{ currentMeta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ userStore.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>

  <!-- 修改密码弹窗 -->
  <el-dialog v-model="passwordVisible" title="修改密码" width="400px">
    <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="80px">
      <el-form-item label="原密码" prop="old_password">
        <el-input v-model="passwordForm.old_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="passwordForm.new_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm_password">
        <el-input v-model="passwordForm.confirm_password" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="passwordVisible = false">取消</el-button>
      <el-button type="primary" @click="submitPassword">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  UserFilled, Odometer, Setting, User, OfficeBuilding, Key, Menu,
  Connection, Document, Folder, Files, Grid, List, Search, Edit,
  Delete, Plus, Minus, Check, Close, Warning, InfoFilled, QuestionFilled,
  Star, Message, Bell, Calendar, Clock, Location, Phone, Picture,
  VideoCamera, Upload, Download, Link, Share, Lock, Unlock, Tools,
  Monitor, DataLine, PieChart, TrendCharts, Histogram
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useMenuStore } from '@/stores/menu'
import { changePassword } from '@/api/auth'

// 图标组件映射
const iconComponents = {
  Odometer: markRaw(Odometer),
  Setting: markRaw(Setting),
  User: markRaw(User),
  OfficeBuilding: markRaw(OfficeBuilding),
  UserFilled: markRaw(UserFilled),
  Key: markRaw(Key),
  Menu: markRaw(Menu),
  Connection: markRaw(Connection),
  Document: markRaw(Document),
  Folder: markRaw(Folder),
  Files: markRaw(Files),
  Grid: markRaw(Grid),
  List: markRaw(List),
  Search: markRaw(Search),
  Edit: markRaw(Edit),
  Delete: markRaw(Delete),
  Plus: markRaw(Plus),
  Minus: markRaw(Minus),
  Check: markRaw(Check),
  Close: markRaw(Close),
  Warning: markRaw(Warning),
  InfoFilled: markRaw(InfoFilled),
  QuestionFilled: markRaw(QuestionFilled),
  Star: markRaw(Star),
  Message: markRaw(Message),
  Bell: markRaw(Bell),
  Calendar: markRaw(Calendar),
  Clock: markRaw(Clock),
  Location: markRaw(Location),
  Phone: markRaw(Phone),
  Picture: markRaw(Picture),
  VideoCamera: markRaw(VideoCamera),
  Upload: markRaw(Upload),
  Download: markRaw(Download),
  Link: markRaw(Link),
  Share: markRaw(Share),
  Lock: markRaw(Lock),
  Unlock: markRaw(Unlock),
  Tools: markRaw(Tools),
  Monitor: markRaw(Monitor),
  DataLine: markRaw(DataLine),
  PieChart: markRaw(PieChart),
  TrendCharts: markRaw(TrendCharts),
  Histogram: markRaw(Histogram)
}

// 根据图标名称获取组件
const getIconComponent = (iconName) => {
  return iconComponents[iconName] || iconComponents.Document
}

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const menuStore = useMenuStore()

const isCollapse = ref(false)
const passwordVisible = ref(false)
const passwordFormRef = ref(null)

const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirm = (rule, value, callback) => {
  if (value !== passwordForm.value.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' }
  ]
}

const currentRoute = computed(() => route.path)
const currentMeta = computed(() => route.meta || {})

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

const handleCommand = async (command) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        type: 'warning'
      })
      await userStore.logout()
      menuStore.resetMenus()
      router.push('/login')
    } catch {
      // 取消操作
    }
  } else if (command === 'password') {
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
    passwordVisible.value = true
  } else if (command === 'profile') {
    ElMessage.info('个人信息功能待开发')
  }
}

const submitPassword = async () => {
  await passwordFormRef.value.validate()
  await changePassword({
    old_password: passwordForm.value.old_password,
    new_password: passwordForm.value.new_password
  })
  ElMessage.success('密码修改成功')
  passwordVisible.value = false
}

// 组件挂载时加载菜单
onMounted(async () => {
  if (!menuStore.isLoaded) {
    await menuStore.fetchUserMenus()
  }
})
</script>

<style lang="scss" scoped>
.main-layout {
  height: 100vh;
}

.aside {
  background-color: #304156;
  transition: width 0.3s;
  overflow: hidden;

  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 16px;
    background-color: #263445;

    .logo-img {
      width: 32px;
      height: 32px;
    }

    .logo-text {
      margin-left: 10px;
      font-size: 18px;
      font-weight: bold;
      color: #fff;
      white-space: nowrap;
    }
  }

  .el-menu {
    border-right: none;
  }
}

.main-container {
  display: flex;
  flex-direction: column;
}

.header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);

  .header-left {
    display: flex;
    align-items: center;

    .collapse-btn {
      font-size: 20px;
      cursor: pointer;
      margin-right: 16px;

      &:hover {
        color: #409eff;
      }
    }
  }

  .header-right {
    .user-info {
      display: flex;
      align-items: center;
      cursor: pointer;

      .username {
        margin: 0 8px;
      }
    }
  }
}

.main {
  background-color: #f0f2f5;
  padding: 20px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
