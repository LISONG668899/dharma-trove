// ============================================================
// 翻译失败记录
//   GET  /api/translate-log?key=你的口令        查看最近的失败记录（只有知道口令的人能看）
//   GET  /api/translate-log?key=你的口令&clear=1 清空记录
//   POST /api/translate-log                     浏览器在“网络中断”时补报一条（服务器收不到的那种失败）
// 口令在 Cloudflare 后台设置：环境变量 LOG_KEY（类型选“密钥”）。
// 只记：时间、原因、页面、所选藏文的长度和开头几个字、耗时。不记读者 IP、设备等任何个人信息。
// ============================================================

const WHY = {
  'upstream-timeout': 'MITRA 超时（95 秒内没译完）',
  'upstream-network': '本站服务器连不上 MITRA',
  'upstream-empty': 'MITRA 回了空译文',
  'upstream-bad-json': 'MITRA 回的内容看不懂',
  'upstream': 'MITRA 出错（原因不明）',
  'not-on-page': '所选文字和原文核对不上',
  'too-long': '选得太长（超过 1500 字符）',
  'network': '读者那边网络中断（浏览器补报）'
}
const explain = (w) =>
  WHY[w] || (w.startsWith('upstream-http-') ? `MITRA 返回错误：${w.slice(14)}` :
             w.startsWith('not-found-') ? `找不到这一页的原文（${w.slice(10)}）` : w)

async function logFail(env, rec) {
  if (!env.TRANSLATIONS) return
  const at = Date.now()
  const meta = {
    at,
    why: String(rec.why || '').slice(0, 100),
    path: String(rec.path || '').slice(0, 160),
    src: String(rec.src || '').slice(0, 80),
    len: Number(rec.len) || 0,
    head: String(rec.head || '').slice(0, 40),
    ms: Number(rec.ms) || 0,
    from: rec.from || 'server'
  }
  const key = `fail:${String(9999999999999 - at).padStart(13, '0')}:${Math.random().toString(36).slice(2, 8)}`
  await env.TRANSLATIONS.put(key, '1', { metadata: meta, expirationTtl: 90 * 24 * 3600 }).catch(() => {})
}

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c])

export async function onRequestPost({ request, env }) {
  let b = {}
  try { b = await request.json() } catch {}
  // 只接受“网络中断”这一种补报，其余失败服务器自己已经记了
  if (b?.why !== 'network' || !String(b?.path || '').startsWith('/')) return new Response(null, { status: 204 })
  await logFail(env, { why: 'network', path: b.path, src: b.src, len: b.len, head: b.head, ms: b.ms, from: 'browser' })
  return new Response(null, { status: 204 })
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url)
  if (!env.LOG_KEY || url.searchParams.get('key') !== env.LOG_KEY) return new Response('Not found', { status: 404 })
  if (!env.TRANSLATIONS) return new Response('没有绑定 KV（TRANSLATIONS）', { status: 500 })

  const rows = []
  let cursor
  do {
    const r = await env.TRANSLATIONS.list({ prefix: 'fail:', cursor, limit: 1000 })
    rows.push(...r.keys)
    cursor = r.list_complete ? undefined : r.cursor
  } while (cursor && rows.length < 3000)

  if (url.searchParams.get('clear') === '1') {
    for (const k of rows) await env.TRANSLATIONS.delete(k.name).catch(() => {})
    return new Response(`已清空 ${rows.length} 条记录`, { headers: { 'content-type': 'text/plain; charset=utf-8' } })
  }

  const count = {}
  for (const k of rows) { const w = k.metadata?.why || '?'; count[w] = (count[w] || 0) + 1 }
  const fmt = (t) => new Date(t).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
  const sum = Object.entries(count).sort((a, b) => b[1] - a[1])
    .map(([w, n]) => `<tr><td>${esc(explain(w))}</td><td class="n">${n}</td></tr>`).join('')
  const list = rows.map((k) => {
    const m = k.metadata || {}
    let page = m.path || ''
    try { page = decodeURIComponent(page) } catch {}
    return `<tr><td>${fmt(m.at)}</td><td>${esc(explain(m.why || ''))}</td><td>${esc(page)}</td>` +
      `<td class="bo">${esc(m.head || '')}${m.len > 30 ? '…' : ''}</td><td class="n">${m.len}</td><td class="n">${m.ms ? (m.ms / 1000).toFixed(1) + ' 秒' : ''}</td></tr>`
  }).join('')

  const html = `<!doctype html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>翻译失败记录</title><style>
body{font-family:system-ui,sans-serif;margin:24px;color:#333}h1{font-size:20px}h2{font-size:16px;margin-top:28px}
table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ddd;padding:4px 8px;text-align:left;vertical-align:top}
th{background:#f6f1e4}.n{text-align:right;white-space:nowrap}.bo{font-family:"Noto Serif Tibetan","Microsoft Himalaya",serif;font-size:15px}
p{color:#666;font-size:13px}</style></head><body>
<h1>翻译失败记录</h1><p>共 ${rows.length} 条，按时间从新到旧（北京时间）。记录保存 90 天后自动删除。不含读者的任何个人信息。</p>
<h2>按原因统计</h2><table><tr><th>原因</th><th>次数</th></tr>${sum || '<tr><td colspan="2">暂无失败记录</td></tr>'}</table>
<h2>明细</h2><table><tr><th>时间</th><th>原因</th><th>页面</th><th>所选藏文开头</th><th>字数</th><th>耗时</th></tr>${list}</table>
</body></html>`
  return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } })
}
