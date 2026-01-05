import request from '@/utils/request'

// 获取插件列表
export function getPluginList(params) {
  return request.get('/v1/plugins/list', { params })
}

// 发现可用插件
export function discoverPlugins() {
  return request.get('/v1/plugins/discover')
}

// 同步插件
export function syncPlugins() {
  return request.post('/v1/plugins/sync')
}

// 获取插件详情
export function getPluginDetail(pluginId) {
  return request.get(`/v1/plugins/${pluginId}`)
}

// 启用插件
export function enablePlugin(pluginId) {
  return request.post(`/v1/plugins/${pluginId}/enable`)
}

// 禁用插件
export function disablePlugin(pluginId) {
  return request.post(`/v1/plugins/${pluginId}/disable`)
}

// 卸载插件
export function uninstallPlugin(pluginId) {
  return request.delete(`/v1/plugins/${pluginId}`)
}

// 上传安装插件
export function uploadPlugin(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/v1/plugins/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 获取插件设置
export function getPluginSettings(pluginId) {
  return request.get(`/v1/plugins/${pluginId}/settings`)
}

// 更新插件设置
export function updatePluginSettings(pluginId, settings) {
  return request.put(`/v1/plugins/${pluginId}/settings`, { settings })
}
