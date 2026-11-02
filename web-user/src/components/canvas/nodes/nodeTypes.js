/**
 * VueFlow 节点类型注册（全部走 BaseNode 配置驱动，T8 节点2 §1）
 * 原始节点类型存 data.nodeType，Schema v2 序列化时回写。
 */
import { markRaw } from 'vue'
import BaseNode from './BaseNode.vue'
import { WF_NODE_TYPE } from '@/utils/graphSerializer'

export const nodeTypes = {
  [WF_NODE_TYPE]: markRaw(BaseNode)
}
