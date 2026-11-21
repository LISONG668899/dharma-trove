// ============================================================
// 藏文选段机器翻译：POST /api/translate-text   { path, text, lang }
// 读者在《甘珠尔》《丹珠尔》等藏文原典里选中一段藏文，点“机器翻译”，译成简体或繁体白话。
// ------------------------------------------------------------
// 引擎：Dharmamitra / MITRA 佛典翻译引擎（日本东北大学；免费，无需密钥）。
//       浏览器不能直接连它，所以由本站服务器代为请求。
//
// 防滥用：
//   · 只翻译本站页面里真实存在的藏文：服务器按 path 自己取这一页，核对所选文字确在页中，
//     别人无法拿这个接口当免费翻译器。
//   · 每次最多 1500 字符。
//   · 绑定了 KV（变量名 TRANSLATIONS）时，译过的句子存起来，以后任何读者选同一句都直接返回，
//     不再请求，也不会因为读者清除浏览器而丢失。
//
// 礼节：Dharmamitra 是免费公开的服务。正式公开前，请写信到 dharmamitra-project@gmail.com 告知对方。
// ============================================================

const MITRA_URL = 'https://dharmamitra.org/api-search/cat-translate/v1/translate'
const MITRA_TIMEOUT_MS = 95000   // 长句可能要 60 秒；对方网关 100 秒截断
const MAX_LEN = 1500

const STYLE = {
  zh: 'Translate faithfully and readably into modern Simplified Chinese prose, using established Chinese Buddhist terminology. Keep the meaning of every clause. Output only the translation.',
  zht: 'Translate faithfully and readably into modern Chinese prose written entirely in Traditional Chinese characters (not Simplified), using established Chinese Buddhist terminology. Keep the meaning of every clause. Output only the translation.'
}

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }
  })

const squash = (s) => s.replace(/\s+/g, '')

function decode(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
    .replace(/&#39;|&#x27;/g, "'").replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(+n))
    .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
    .replace(/&amp;/g, '&')
}

async function sha(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return [...new Uint8Array(buf)].slice(0, 12).map((b) => b.toString(16).padStart(2, '0')).join('')
}

async function viaMitra(text, lang) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), MITRA_TIMEOUT_MS)
  try {
    const r = await fetch(MITRA_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/json', accept: 'application/json' },
      body: JSON.stringify({
        input_tibetan: text,
        input_chinese: '',
        input_pali: '',
        input_sanskrit: '',
        focus: 'tibetan',
        target_language: 'modern chinese',
        context: 'Classical Tibetan Buddhist canonical literature (Derge Kangyur and Tengyur).',
        style_instruction: STYLE[lang]
      }),
      signal: ctrl.signal
    })
    if (!r.ok) throw new Error('mitra ' + r.status)
    const data = await r.json()
    const out = typeof data?.translation === 'string' ? data.translation.trim() : ''
    if (!out) throw new Error('mitra empty')
    return out
  } finally {
    clearTimeout(timer)
  }
}

export async function onRequestPost({ request, env }) {
  let body
  try { body = await request.json() } catch { return json({ ok: false, error: 'bad-request' }, 400) }
  let p = String(body?.path || '')
  const lang = String(body?.lang || '')
  const text = String(body?.text || '').replace(/\s+/g, ' ').trim()
  if (text.length > MAX_LEN) return json({ ok: false, error: 'too-long' }, 400)
  if (!STYLE[lang] || !p.startsWith('/') || p.includes('..') || p.length > 600 ||
      text.length < 2 || !/[ༀ-࿿]/.test(text)) {
    return json({ ok: false, error: 'bad-request' }, 400)
  }

  // 核对：所选文字必须出自这一页。
  // 藏文原典的阅读页正文不在网页里，而在 /canon/…/经号/分段.json，这时按 src 核对那个文件。
  const src = String(body?.src || '')
  const useSrc = /^\/canon\/(kangyur|tengyur)\/[\w-]+\/\d+\.json$/.test(src)
  const pageRes = await env.ASSETS.fetch(new Request(new URL(useSrc ? src : p, request.url).toString()))
  if (!pageRes.ok) return json({ ok: false, error: 'not-found' }, 404)
  const raw = await pageRes.text()
  let pageText = ''
  if (useSrc) {
    try { pageText = JSON.parse(raw).paras.map((x) => x[1]).join('') } catch { pageText = '' }
  } else {
    pageText = decode(raw)
  }
  if (!squash(pageText).includes(squash(text))) return json({ ok: false, error: 'not-on-page' }, 403)

  // 译过的直接返回
  const key = `sel:${lang}:${await sha(text)}`
  if (env.TRANSLATIONS) {
    const hit = await env.TRANSLATIONS.get(key, 'json').catch(() => null)
    if (hit?.text) return json({ ok: true, text: hit.text, cached: true })
  }

  let out = ''
  try { out = await viaMitra(text, lang) } catch {}
  if (!out) return json({ ok: false, error: 'upstream' }, 502)

  if (env.TRANSLATIONS) {
    await env.TRANSLATIONS.put(key, JSON.stringify({ text: out, at: Date.now() })).catch(() => {})
  }
  return json({ ok: true, text: out })
}

export async function onRequest() {
  return json({ ok: false, error: 'method-not-allowed' }, 405)
}
