/**
 * 变量类型系统（Schema v2）
 * 溯源：base/plugins/agent/services/graph_validator.py L62-L142
 * （normalize_type / is_valid_type / types_compatible 逐条移植，规则必须与服务端一致）
 * PRD §4.2 类型系统、§4.3 兼容矩阵。
 */

// 标量类型全集（与服务端 _SCALAR_TYPES 一致）
export const SCALAR_TYPES = new Set([
  'string', 'number', 'integer', 'boolean', 'date',
  'file', 'image', 'object', 'chunk', 'message', 'document',
  'any', 'unknown', 'secret', 'stream'
])

const ARRAY_RE = /^array<(.+)>$/

/**
 * 归一类型写法：chunk[] → array<chunk>；去空白小写
 * @param {*} t
 * @returns {string}
 */
export function normalizeType(t) {
  if (typeof t !== 'string') return 'unknown'
  const s = t.trim().toLowerCase()
  if (s.endsWith('[]')) return `array<${s.slice(0, -2).trim()}>`
  return s
}

/**
 * 取数组元素类型；非数组返回 null
 * @param {string} t
 * @returns {string|null}
 */
export function arrayInner(t) {
  const m = ARRAY_RE.exec(t)
  return m ? m[1].trim() : null
}

/**
 * 类型写法是否合法
 * @param {*} t
 * @returns {boolean}
 */
export function isValidType(t) {
  const nt = normalizeType(t)
  const inner = arrayInner(nt)
  if (inner !== null) return isValidType(inner)
  return SCALAR_TYPES.has(nt)
}

/**
 * 类型兼容矩阵（PRD §4.3，与服务端 types_compatible 一致）：
 * 同型直连；integer→number 加宽；任意→any 透传；any→具体禁止；
 * array<T>→array<U> 按元素兼容；unknown→任意禁止。
 * @param {*} src 源端口类型
 * @param {*} dst 目标端口类型
 * @returns {boolean}
 */
export function typesCompatible(src, dst) {
  const s = normalizeType(src)
  const d = normalizeType(dst)
  if (d === 'any') return s !== 'unknown'
  if (s === 'any') return d === 'any'
  if (s === 'unknown' || d === 'unknown') return false
  if (s === d) return true
  if (s === 'integer' && d === 'number') return true
  const sInner = arrayInner(s)
  const dInner = arrayInner(d)
  if (sInner !== null && dInner !== null) return typesCompatible(sInner, dInner)
  return false
}
