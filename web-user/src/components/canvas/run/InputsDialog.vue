<template>
  <!-- 试跑输入对话框：按 start 节点 inputs 渲染（T12 节点1 Q5） -->
  <el-dialog v-model="visible" title="试跑输入" width="480px" :close-on-click-modal="false">
    <el-form label-position="top">
      <el-form-item
        v-for="inp in inputs"
        :key="inp.name"
        :label="inp.name"
        :required="!!inp.required"
      >
        <el-input
          v-model="form[inp.name]"
          :placeholder="inp.type ? `类型：${inp.type}` : '请输入'"
        />
      </el-form-item>
      <el-empty v-if="!inputs.length" description="该工作流无需输入变量" :image-size="60" />
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="starting" @click="onConfirm">开始试跑</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  /** start 节点 inputs 端口声明 */
  inputs: { type: Array, default: () => [] },
  starting: { type: Boolean, default: false }
})
const emit = defineEmits(['confirm'])

const visible = ref(false)
const form = reactive({})

function open() {
  Object.keys(form).forEach((k) => delete form[k])
  props.inputs.forEach((inp) => { form[inp.name] = '' })
  visible.value = true
}

function onConfirm() {
  // 必填校验（前端体验，服务端 E-100 权威）
  for (const inp of props.inputs) {
    if (inp.required && !String(form[inp.name] ?? '').trim()) {
      ElMessage.warning(`请填写必填输入：${inp.name}`)
      return
    }
  }
  const payload = {}
  props.inputs.forEach((inp) => { if (form[inp.name] !== '') payload[inp.name] = form[inp.name] })
  emit('confirm', payload)
}

function close() { visible.value = false }

const hasInputs = computed(() => props.inputs.length > 0)
defineExpose({ open, close, hasInputs })
</script>
