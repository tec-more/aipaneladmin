<template>
  <!-- 节点配置表单（T10）：按 registry fields 声明驱动渲染，单一事实源 -->
  <el-form label-position="top" size="default" class="node-config-form">
    <template v-for="f in fields" :key="f.key">
      <el-form-item :required="!!f.required">
        <template #label>
          <span class="field-label">{{ f.label }}</span>
          <el-tooltip v-if="f.help" :content="f.help" placement="top" :show-after="200">
            <el-icon class="field-help"><QuestionFilled /></el-icon>
          </el-tooltip>
        </template>

        <!-- enum -->
        <el-select
          v-if="f.type === 'enum'"
          :model-value="local[f.key]"
          style="width: 100%"
          @update:model-value="setValue(f, $event)"
        >
          <el-option v-for="o in f.options || []" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>

        <!-- boolean -->
        <el-switch
          v-else-if="f.type === 'boolean'"
          :model-value="!!local[f.key]"
          @update:model-value="setValue(f, $event)"
        />

        <!-- number / integer -->
        <el-input-number
          v-else-if="f.type === 'number' || f.type === 'integer'"
          :model-value="local[f.key]"
          :min="f.min" :max="f.max"
          :step="f.step || (f.type === 'integer' ? 1 : 0.1)"
          :precision="f.type === 'integer' ? 0 : undefined"
          style="width: 100%"
          controls-position="right"
          @update:model-value="setValue(f, $event)"
        />

        <!-- json（object / array） -->
        <template v-else-if="f.widget === 'json' || f.type === 'object' || f.type.startsWith('array')">
          <el-input
            v-if="f.widget !== 'resource_ref'"
            :model-value="jsonText[f.key]"
            type="textarea" :rows="3"
            placeholder='JSON，如 {"key": "value"} 或 ["a", "b"]'
            @update:model-value="onJsonInput(f, $event)"
            @blur="commitJson(f)"
          />
          <div v-if="jsonError[f.key]" class="field-error">{{ jsonError[f.key] }}</div>
        </template>

        <!-- resource_ref（T11：授权选择器；workflow 走 M8 归属模型） -->
        <template v-else-if="f.widget === 'resource_ref'">
          <WorkflowSelect
            v-if="f.resourceKind === 'workflow'"
            :model-value="local[f.key]"
            :placeholder="resourcePlaceholder(f)"
            @update:model-value="setValue(f, $event)"
          />
          <ResourceSelect
            v-else
            :model-value="local[f.key]"
            :resource-type="f.resourceKind"
            :field-type="f.type"
            :placeholder="resourcePlaceholder(f)"
            @update:model-value="setValue(f, $event)"
          />
        </template>

        <!-- text / textarea（prompt 类带变量助手） -->
        <template v-else-if="f.type === 'text'">
          <VarInsertHelper
            :model-value="local[f.key] ?? ''"
            :variables="availableVars"
            @update:model-value="setValue(f, $event)"
          />
        </template>

        <!-- string -->
        <el-input
          v-else
          :model-value="local[f.key]"
          @update:model-value="setValue(f, $event)"
        />

        <div v-if="errors[f.key]" class="field-error">{{ errors[f.key] }}</div>
      </el-form-item>
    </template>
  </el-form>
</template>

<script setup>
/**
 * 字段类型驱动表单渲染器（T10）
 * 约束来源：registry fields（required/min/max/options 与 PRD/E-100 对齐）。
 * 写回：防抖 500ms 调 store.updateNodeConfig（并入 T8 历史栈与自动保存链）。
 */
import { reactive, ref, watch, computed } from 'vue'
import { getNodeMeta } from '@validator'
import VarInsertHelper from './VarInsertHelper.vue'
import ResourceSelect from './ResourceSelect.vue'
import WorkflowSelect from './WorkflowSelect.vue'

const props = defineProps({
  node: { type: Object, required: true }
})
const emit = defineEmits(['update-config'])

const meta = computed(() => getNodeMeta(props.node?.data?.nodeType || props.node?.type))
const fields = computed(() => meta.value?.fields || [])

// 本地表单态：config 拷贝，缺失字段用 fields 默认值补齐（R-A）
const local = reactive({})
const jsonText = reactive({})
const jsonError = reactive({})
const errors = reactive({})

function fillDefaults() {
  const cfg = props.node?.data?.config || {}
  for (const k of Object.keys(local)) delete local[k]
  Object.assign(local, cfg)
  for (const f of fields.value) {
    if (local[f.key] === undefined && f.default !== undefined) local[f.key] = f.default
    if (f.widget === 'json' || f.type === 'object' || (f.type || '').startsWith('array')) {
      jsonText[f.key] = local[f.key] == null ? '' : JSON.stringify(local[f.key], null, 2)
      jsonError[f.key] = ''
    }
    errors[f.key] = ''
  }
}
watch(() => props.node?.id, fillDefaults, { immediate: true })

/** 可引用变量：上游节点输出（{{节点id.端口}} 形式提示） */
const availableVars = computed(() => [])

let timer = null
function scheduleCommit() {
  clearTimeout(timer)
  timer = setTimeout(commit, 500)
}
function commit() {
  // 必填与范围校验（前端体验层，服务端 E-100 权威）
  let ok = true
  for (const f of fields.value) {
    errors[f.key] = ''
    const v = local[f.key]
    if (f.required && (v == null || v === '' || (Array.isArray(v) && !v.length))) {
      errors[f.key] = `${f.label} 必填`
      ok = false
    } else if ((f.type === 'number' || f.type === 'integer') && v != null) {
      if (f.min != null && v < f.min) { errors[f.key] = `不能小于 ${f.min}`; ok = false }
      if (f.max != null && v > f.max) { errors[f.key] = `不能大于 ${f.max}`; ok = false }
    }
  }
  emit('update-config', { ...local })
  return ok
}

function setValue(f, v) {
  local[f.key] = v
  scheduleCommit()
}
function onJsonInput(f, v) {
  jsonText[f.key] = v
}
function commitJson(f) {
  const raw = (jsonText[f.key] || '').trim()
  if (!raw) { local[f.key] = f.type === 'object' ? {} : []; jsonError[f.key] = ''; scheduleCommit(); return }
  try {
    const parsed = JSON.parse(raw)
    local[f.key] = parsed
    jsonError[f.key] = ''
    scheduleCommit()
  } catch {
    jsonError[f.key] = 'JSON 格式错误，未写回'
  }
}
function resourcePlaceholder(f) {
  const kind = { model: '模型', kb: '知识库', workflow: '工作流' }[f.resourceKind] || '资源'
  return `选择已授权${kind}${f.type.startsWith('array') ? '（可多选）' : ''}`
}
</script>

<style scoped>
.field-label { font-weight: 500; }
.field-help { margin-left: 4px; color: var(--el-text-color-secondary); cursor: help; vertical-align: -2px; }
.field-error { color: var(--el-color-danger); font-size: 12px; line-height: 1.4; margin-top: 2px; }
</style>
