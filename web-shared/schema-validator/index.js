/**
 * @aipanel/schema-validator —— Schema v2 图校验器（纯函数，前后台共享）
 * T8 交付；T9 复用并扩展 v1→v2 转换器。
 * 错误码与 issue 结构与服务端 graph_validator.py 完全对齐（双源渲染零转换）。
 */
export { SCALAR_TYPES, normalizeType, isValidType, typesCompatible, arrayInner } from './types.js'
export {
  NODE_REGISTRY, NODE_CATEGORIES, FORBIDDEN_TYPES, TYPE_ALIASES,
  getNodeMeta, normalizeNodeType, resolvePortType
} from './nodeRegistry.js'
export { CODES, LEVEL_ERROR, LEVEL_WARNING, makeIssue } from './rules/codes.js'
export { validateConnection, wouldCreateCycle } from './rules/connection.js'
export { validateGraph } from './rules/graph.js'

// ===== JSDoc 类型（与 T8 节点2 §4 一致）=====
/**
 * @typedef {Object} PortDecl
 * @property {string} name @property {string} type
 * @property {string} [from] @property {boolean} [required]
 *
 * @typedef {Object} NodeV2
 * @property {string} id @property {string} type
 * @property {{x:number, y:number}} position
 * @property {{label:string, config:Object, inputs?:PortDecl[], outputs?:PortDecl[]}} data
 *
 * @typedef {Object} EdgeV2
 * @property {string} id @property {string} source @property {string} sourceHandle
 * @property {string} target @property {string} targetHandle @property {string} [condition]
 *
 * @typedef {Object} VariableV2
 * @property {string} name @property {string} type
 * @property {boolean} [required] @property {string} [source] @property {boolean} [sensitive]
 *
 * @typedef {Object} GraphV2
 * @property {number} schema_version
 * @property {{name:string, description?:string, icon?:string}} meta
 * @property {VariableV2[]} variables
 * @property {NodeV2[]} nodes
 * @property {EdgeV2[]} edges
 * @property {Object} settings
 *
 * @typedef {Object} ValidationIssue
 * @property {string} code @property {'error'|'warning'} level
 * @property {string} [node_id] @property {string} [edge_id] @property {string} [field]
 * @property {string} message
 */
