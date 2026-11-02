import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'path'

// 用户侧站点（T7）：独立工程，dev 端口 3100，避免与后台 web/(3000) 冲突
export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts'
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts'
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      // 共享校验器包（T8；T9 复用）：源码直引，免 monorepo 基建
      '@validator': path.resolve(__dirname, '../web-shared/schema-validator/index.js')
    }
  },
  server: {
    port: 3100,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9998',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
