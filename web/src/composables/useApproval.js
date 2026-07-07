/**
 * 审批检测 Composable —— 业务页面引入，自动检测当前模型是否有审批规则
 *
 * 用法:
 *   import { useApproval } from '@/composables/useApproval'
 *   const { hasApproval, approvalFlows, checkModel, canApproveCreate, canApproveUpdate, canApproveDelete } = useApproval()
 *   onMounted(() => checkModel('purchase_order'))
 *
 * 返回:
 *   hasApproval       - Boolean，当前模型是否有审批规则
 *   approvalFlows     - 匹配的流程列表
 *   loading           - 检测中
 *   checkModel(model) - 触发检测（页面 onMounted 时调用）
 *   canApproveCreate / canApproveUpdate / canApproveDelete - 各动作是否需要审批
 *   getFlowForAction(action) - 获取指定动作的流程信息
 */
import { ref, computed } from 'vue'
import { checkApprovalForModel } from '@/api/approval'

export function useApproval() {
  const loading = ref(false)
  const approvalData = ref(null) // { require_approval, flows: [...] }

  const hasApproval = computed(() => {
    return approvalData.value?.require_approval === true
  })

  const approvalFlows = computed(() => {
    return approvalData.value?.flows || []
  })

  const allActions = computed(() => {
    const actions = new Set()
    for (const flow of approvalFlows.value) {
      for (const a of flow.actions || []) {
        actions.add(a)
      }
    }
    return [...actions]
  })

  const canApproveCreate = computed(() => allActions.value.includes('create'))
  const canApproveUpdate = computed(() => allActions.value.includes('update'))
  const canApproveDelete = computed(() => allActions.value.includes('delete'))

  function getFlowForAction(action) {
    return approvalFlows.value.find(f => (f.actions || []).includes(action)) || null
  }

  async function checkModel(model) {
    if (!model) return
    loading.value = true
    try {
      const res = await checkApprovalForModel(model)
      if (res.code === 0 && res.data) {
        approvalData.value = res.data
      } else {
        approvalData.value = null
      }
    } catch {
      approvalData.value = null
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    hasApproval,
    approvalFlows,
    allActions,
    canApproveCreate,
    canApproveUpdate,
    canApproveDelete,
    checkModel,
    getFlowForAction,
  }
}
