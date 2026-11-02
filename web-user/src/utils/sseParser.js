/**
 * SSE 解析器（T12）
 * 用 fetch ReadableStream 消费 text/event-stream（EventSource 不支持 POST/Bearer，Q1 裁定）。
 * 契约：后端 sse_format —— `event: {type}\ndata: {json}\n\n`，seq 在 data 内。
 * 处理：跨 chunk 缓冲、`\n\n` 分帧、多行 data 拼接、注释行(以:开头)忽略。
 */

const decoder = new TextDecoder('utf-8')

/**
 * 解析单帧文本为 {event, data}
 * @param {string} raw 帧文本（不含结尾空行）
 * @returns {{event:string, data:Object}|null}
 */
function parseFrame(raw) {
  let event = 'message'
  const dataLines = []
  for (const line of raw.split(/\r?\n/)) {
    if (!line || line.startsWith(':')) continue
    const idx = line.indexOf(':')
    const field = idx === -1 ? line : line.slice(0, idx)
    let value = idx === -1 ? '' : line.slice(idx + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    if (field === 'event') event = value
    else if (field === 'data') dataLines.push(value)
  }
  if (!dataLines.length) return null
  let data = {}
  try {
    data = JSON.parse(dataLines.join('\n'))
  } catch {
    data = { raw: dataLines.join('\n') }
  }
  return { event, data }
}

/**
 * 消费 SSE 流（fetch Response.body）
 * @param {ReadableStreamDefaultReader} reader
 * @param {(frame:{event:string,data:Object})=>void} onFrame 每帧回调
 * @returns {Promise<void>} 流结束 resolve；解析异常不中断（单帧容错）
 */
export async function consumeSseStream(reader, onFrame) {
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // 按空行分帧（\r\n\r\n 兼容）
    let idx
    while ((idx = buffer.search(/\r?\n\r?\n/)) !== -1) {
      const raw = buffer.slice(0, idx)
      buffer = buffer.slice(idx).replace(/^\r?\n\r?\n/, '')
      const frame = parseFrame(raw)
      if (frame) {
        try { onFrame(frame) } catch { /* 单帧回调异常不中断流 */ }
      }
    }
  }
  // 尾部残帧
  if (buffer.trim()) {
    const frame = parseFrame(buffer)
    if (frame) { try { onFrame(frame) } catch { /* 忽略 */ } }
  }
}
