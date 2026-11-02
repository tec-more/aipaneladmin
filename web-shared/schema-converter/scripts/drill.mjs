/**
 * 存量转换演练脚本（T9；架构 06 §3 高风险管控：逐图 diff 报告）
 * 用法：
 *   node scripts/drill.mjs <导出目录> [报告输出路径]
 * 输入：目录下逐图 JSON 文件（人工从库导出 Agent.graph_definition，单文件单图；
 *       或单文件为 { name, graph } 包裹）。
 * 边界（Q4 裁定）：只读演练——不连接数据库、不回写任何数据。
 * 产物：控制台摘要 + drill-report.json（逐图 diff 明细）。
 */
import { readdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { convertV1ToV2 } from '../index.js'

const [dir = './samples', out = './drill-report.json'] = process.argv.slice(2)

const files = (await readdir(dir)).filter((f) => f.endsWith('.json'))
if (!files.length) {
  console.error(`未找到导出文件：${dir}（请将存量 Agent.graph_definition 导出为单图 JSON 放入该目录）`)
  process.exit(1)
}

const details = []
const totals = { files: 0, ok: 0, degraded: 0, failed: 0, errors: 0, warnings: 0 }

for (const file of files) {
  totals.files += 1
  let v1
  try {
    const raw = JSON.parse(await readFile(path.join(dir, file), 'utf8'))
    v1 = raw.graph && typeof raw.graph === 'object' ? raw.graph : raw
  } catch (e) {
    totals.failed += 1
    details.push({ file, status: 'failed', reason: `JSON 解析失败：${e.message}` })
    continue
  }
  const r = convertV1ToV2(v1, { name: file.replace(/\.json$/, '') })
  const errors = r.issues.filter((i) => i.level === 'error')
  const warnings = r.issues.filter((i) => i.level === 'warning')
  totals.errors += errors.length
  totals.warnings += warnings.length
  let status = 'ok'
  if (!r.graph) { status = 'failed'; totals.failed += 1 }
  else if (r.report.summary.degraded > 0 || errors.length > 0) { status = 'degraded'; totals.degraded += 1 }
  else totals.ok += 1
  details.push({
    file,
    status,
    summary: r.report.summary,
    nodeDiffs: r.report.nodeDiffs,
    edgeDiffs: r.report.edgeDiffs,
    errors: errors.map((i) => `${i.code} ${i.message}`),
    warnings: warnings.map((i) => `${i.code} ${i.message}`)
  })
}

const report = {
  generated_at: new Date().toISOString(),
  source_dir: path.resolve(dir),
  readonly: true,
  totals,
  details
}
await writeFile(out, JSON.stringify(report, null, 2), 'utf8')

console.log('=== 存量转换演练报告（只读，未回写）===')
console.log(`图文件：${totals.files}；可直接迁移：${totals.ok}；需人工处理：${totals.degraded}；失败：${totals.failed}`)
console.log(`校验错误：${totals.errors}；降级提示：${totals.warnings}`)
console.log(`明细报告：${path.resolve(out)}`)
