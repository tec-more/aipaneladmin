/**
 * @aipanel/schema-converter —— v1→v2 转换器（纯函数零依赖，前后台共享）
 * T9 交付。输入：Agent.graph_definition（nodes/edges）；输出：ConvertResult。
 */
export { V1_NODE_MAPPING, DEFAULT_TARGET_HANDLE, DEFAULT_SOURCE_HANDLE, mapConditionBranch } from './mapping.js'
export { W_CODES, makeWarn, createReport } from './report.js'
export { convertV1ToV2 } from './converter.js'

/**
 * @typedef {Object} V1Node
 * @property {string} id @property {string} type
 * @property {Object} [data] @property {{x:number,y:number}} [position]
 *
 * @typedef {Object} V1Edge
 * @property {string} source @property {string} target @property {string} [condition]
 *
 * @typedef {Object} V1Graph
 * @property {V1Node[]} nodes @property {V1Edge[]} [edges]
 *
 * @typedef {Object} ConvertResult
 * @property {Object|null} graph
 * @property {Array<Object>} issues
 * @property {{summary:{total:number,converted:number,degraded:number,failed:number},
 *            nodeDiffs:Array<Object>, edgeDiffs:Array<Object>}} report
 */
