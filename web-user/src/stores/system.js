import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getSystemConfig } from '@/api/common'

// 系统配置 store（用户侧裁剪版：仅需产品名/版本，对齐 web/ 加载模式）
export const useSystemStore = defineStore('system', () => {
  const app_name = ref('AIPanelAdmin')
  const app_version = ref('v0.1.0')
  const frontend_name = ref('')
  const debug = ref(false)
  const loaded = ref(false)

  /**
   * 加载系统公共配置
   * @param {boolean} force - 是否强制刷新
   */
  async function loadConfig(force = false) {
    if (loaded.value && !force) return
    try {
      const res = await getSystemConfig()
      const data = res.data || res
      if (data.app_name != null) app_name.value = data.app_name
      if (data.app_version != null) app_version.value = data.app_version
      if (data.frontend_name != null) frontend_name.value = data.frontend_name
      if (typeof data.debug === 'boolean') debug.value = data.debug
      loaded.value = true
    } catch (e) {
      // 加载失败使用默认值，不阻断骨架渲染
    }
  }

  const productName = computed(() => frontend_name.value || app_name.value)

  return {
    app_name,
    app_version,
    frontend_name,
    debug,
    loaded,
    loadConfig,
    productName
  }
})
