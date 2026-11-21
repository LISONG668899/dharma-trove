<script setup lang="ts">
// 划线收藏：读者在文章正文里选中一段文字，选区下方出现“划线收藏”按钮；
// 收藏过的段落以后再打开这篇文章，会自动显示金色下划线。
// 选中一段已经划过线的文字，按钮变成“取消划线”。
// 在《甘珠尔》《丹珠尔》等藏文原典里，选中藏文时还会多一个“机器翻译”按钮：
// 选区自动扩到完整的句子（以“།”断句），送到本站服务器 /api/translate-text 翻译，
// 译文可以复制，也可以连同藏文原文一起收藏。
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useData, useRoute, withBase } from 'vitepress'
import {
  passages, loadPassages, addPassage, removePassage, findPassage, passagesOf,
  normPath, squash, isTrad, watchScript, T
} from '../saved'

const route = useRoute()
const { page, frontmatter } = useData()
const CATS = ['唯识', '中观', '华严', '禅宗', '净土', '大手印', '大圆满', '综合', '甘珠尔', '丹珠尔']
const rel = computed(() => page.value.relativePath || '')
const cat = computed(() => rel.value.split('/')[0])
const CANON = ['甘珠尔', '丹珠尔']
// 藏文原典连目录页也可以划线、翻译
const isArticle = computed(() => (CATS.includes(cat.value) && !rel.value.endsWith('index.md')) || CANON.includes(cat.value))
// 阅读页（/甘珠尔/read?t=..&p=..）由 CanonReader 告诉我们当前是哪部经、哪一段
const reader = ref<{ path: string; title: string; cat: string; src: string } | null>(null)
const path = computed(() => reader.value?.path || normPath(route.path))
const title = computed(() => reader.value?.title || frontmatter.value.title || page.value.title || '')
function onReader(e: Event) {
  reader.value = (e as CustomEvent).detail
  btn.value = null
  card.value = null
  repaintSoon()
  setTimeout(jumpIfAsked, 150)
}

const btn = ref<{ top: number; left: number; existing: string | null; bo: boolean } | null>(null)
const toast = ref('')
let picked = ''
let pickedRange: Range | null = null

/* ---------- 选区 ---------- */
let timer: any
function check() {
  if (!isArticle.value) { btn.value = null; return }
  const sel = window.getSelection()
  const root = document.querySelector('.vp-doc')
  if (!sel || sel.isCollapsed || !sel.rangeCount || !root) { btn.value = null; return }
  const range = sel.getRangeAt(0)
  if (!root.contains(range.commonAncestorContainer)) { btn.value = null; return }
  const text = sel.toString().replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim()
  if (squash(text).length < 2) { btn.value = null; return }
  const rects = range.getClientRects()
  const r = rects.length ? rects[rects.length - 1] : range.getBoundingClientRect()
  if (card.value && squash(text) === squash(card.value.source)) { btn.value = null; return }   // 正在翻译的就是这一句
  const half = /[\u0F00-\u0FFF]/.test(text) ? 120 : 70
  btn.value = {
    top: r.bottom + window.scrollY + 12,
    left: Math.min(Math.max(r.left + r.width / 2 + window.scrollX, half + 8), window.innerWidth - half - 8),
    bo: /[\u0F00-\u0FFF]/.test(text),
    existing: (() => { const k = squash(text); const o = occurrenceOf(text, range); return passagesOf(path.value).find((p) => squash(p.text) === k && (p.occ || 0) === o)?.id || null })()
  }
  picked = text
  pickedRange = range.cloneRange()
}
const later = () => { clearTimeout(timer); timer = setTimeout(check, 180) }

function onClick() {
  if (!btn.value) return
  if (btn.value.existing) {
    removePassage(btn.value.existing)
    flash(T('已取消划线', '已取消劃線'))
  } else {
    addPassage(path.value, title.value, cat.value, picked, occurrenceOf(picked, pickedRange))
    flash(T('已划线收藏，可在“我的收藏”里导出', '已劃線收藏，可在“我的收藏”裡導出'))
  }
  btn.value = null
  window.getSelection()?.removeAllRanges()
  paint()
}


/* ---------- 藏文选段机器翻译 ---------- */
const SHAD = /[\u0F0D-\u0F12\u0F14]/
const BLOCK = '.dt-bo, p, h1, h2, h3, h4, li, blockquote, td'
function blockOf(node: Node, root: Element) {
  const el = (node.nodeType === 1 ? node : node.parentElement) as Element | null
  const b = el?.closest(BLOCK)
  return b && root.contains(b) ? b : null
}
function offsetIn(block: Element, node: Node, off: number) {
  const r = document.createRange()
  r.setStart(block, 0)
  r.setEnd(node, off)
  return r.toString().length
}
function pointAt(block: Element, offset: number): [Node, number] {
  const w = document.createTreeWalker(block, NodeFilter.SHOW_TEXT)
  let n: Node | null
  let left = offset
  let last: Node | null = null
  while ((n = w.nextNode())) {
    const len = (n as Text).data.length
    if (left <= len) return [n, left]
    left -= len
    last = n
  }
  return last ? [last, (last as Text).data.length] : [block, 0]
}
/** 选区扩到完整句子：开头退到上一个“།”之后，结尾进到下一个“།”为止——不同读者选同一句，送出的文字相同，译文可以共享 */
function expand(range: Range, root: Element): Range {
  const sb = blockOf(range.startContainer, root)
  const eb = blockOf(range.endContainer, root)
  if (!sb || !eb) return range
  const st = sb.textContent || ''
  const et = eb.textContent || ''
  let i = offsetIn(sb, range.startContainer, range.startOffset)
  while (i > 0 && !SHAD.test(st[i - 1])) i--
  while (i < st.length && (SHAD.test(st[i]) || /\s/.test(st[i]))) i++
  let j = offsetIn(eb, range.endContainer, range.endOffset)
  if (!(j > 0 && SHAD.test(et[j - 1]))) { while (j < et.length && !SHAD.test(et[j])) j++ }
  while (j < et.length && SHAD.test(et[j])) j++
  const r = document.createRange()
  const [sn, so] = pointAt(sb, i)
  const [en, eo] = pointAt(eb, j)
  r.setStart(sn, so)
  r.setEnd(en, eo)
  return r.collapsed ? range : r
}

const card = ref<{ source: string; text: string; loading: boolean; error: string; occ: number } | null>(null)
const copied = ref(false)
const ERR: Record<string, [string, string]> = {
  'too-long': ['选得太长了，请少选一些（1500 字符以内）', '選得太長了，請少選一些（1500 字元以內）'],
  'upstream': ['翻译服务（MITRA）这会儿忙或没有回应，请稍后再试', '翻譯服務（MITRA）這會兒忙或沒有回應，請稍後再試'],
  'not-on-page': ['所选文字和原文核对不上，请重新选取后再试', '所選文字和原文核對不上，請重新選取後再試'],
  'not-found': ['找不到这一页的原文，请刷新页面后再试', '找不到這一頁的原文，請重新整理頁面後再試'],
  'network': ['网络连接中断了，请检查网络后再试', '網路連線中斷了，請檢查網路後再試'],
  'default': ['翻译失败，请稍后再试', '翻譯失敗，請稍後再試']
}

async function translate() {
  if (!btn.value) return
  btn.value = null
  const root = document.querySelector('.vp-doc')
  let text = picked
  let range = pickedRange
  if (pickedRange && root) {
    range = expand(pickedRange, root)
    text = range.toString().replace(/\s+/g, ' ').trim() || picked
    const sel = window.getSelection()
    sel?.removeAllRanges()
    sel?.addRange(range)
  }
  if (!text) return
  card.value = { source: text, text: '', loading: true, error: '', occ: occurrenceOf(text, range) }
  copied.value = false
  await runTranslate(text)
}

// 请求一次；网络中断或翻译服务没回应时，自动再试一次
async function askOnce(text: string): Promise<{ ok?: boolean; text?: string; error?: string }> {
  try {
    const r = await fetch('/api/translate-text', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ path: route.path, src: reader.value?.src || '', text, lang: isTrad.value ? 'zht' : 'zh' })
    })
    const d = await r.json().catch(() => null)
    if (d) return d
    return { ok: false, error: r.status >= 500 ? 'upstream' : 'default' }
  } catch {
    return { ok: false, error: 'network' }
  }
}

async function runTranslate(text: string) {
  if (!card.value || card.value.source !== text) return
  card.value.loading = true
  card.value.error = ''
  let d = await askOnce(text)
  if (!d.ok && (d.error === 'network' || d.error === 'upstream') && card.value?.source === text) {
    await new Promise((res) => setTimeout(res, 2000))
    d = await askOnce(text)
  }
  if (!d.ok && d.error === 'network') {
    // 网络中断的失败服务器收不到，等网络恢复时由浏览器补报一条（不含任何读者信息）
    const report = JSON.stringify({ why: 'network', path: route.path, src: reader.value?.src || '', len: text.length, head: text.slice(0, 30) })
    const send = () => fetch('/api/translate-log', { method: 'POST', headers: { 'content-type': 'application/json' }, body: report, keepalive: true }).catch(() => {})
    if (navigator.onLine) send()
    else window.addEventListener('online', send, { once: true })
  }
  if (!card.value || card.value.source !== text) return
  if (d.ok && d.text) card.value.text = d.text
  else card.value.error = T(...(ERR[d.error || 'default'] || ERR.default))
  card.value.loading = false
}

function retryCard() {
  if (card.value) runTranslate(card.value.source)
}

const cardSaved = computed(() => {
  const c = card.value
  if (!c || !c.text) return false
  const k = squash(c.source)
  return passagesOf(path.value).some((p) => squash(p.text) === k && p.tr === c.text)
})

function saveCard() {
  const c = card.value
  if (!c || !c.text) return
  addPassage(path.value, title.value, cat.value, c.source, c.occ, c.text)
  flash(T('原文与译文已收藏', '原文與譯文已收藏'))
  paint()
}

async function copyCard() {
  const c = card.value
  if (!c?.text) return
  try { await navigator.clipboard.writeText(c.source + '\n' + c.text); copied.value = true } catch {}
}

function closeCard() {
  card.value = null
  window.getSelection()?.removeAllRanges()
}

let toastTimer: any
function flash(msg: string) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2200)
}

/* ---------- 划线显示（CSS Custom Highlight API，不改动页面文字，不影响简繁切换） ---------- */
function flatten() {
  const root = document.querySelector('.vp-doc')
  const map: [Text, number][] = []
  let flat = ''
  if (!root) return { flat, map }
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let n: Node | null
  while ((n = w.nextNode())) {
    const t = n as Text
    if (t.parentElement?.closest('.header-anchor')) continue
    const d = t.data
    for (let i = 0; i < d.length; i++) {
      if (/\s/.test(d[i])) continue
      flat += d[i]
      map.push([t, i])
    }
  }
  return { flat, map }
}

/** 同样的文字在文中可能出现多次（比如标题和正文），记下读者划的是第几处 */
function occurrenceOf(text: string, range: Range | null) {
  if (!range) return 0
  const { flat, map } = flatten()
  const k = squash(text)
  let at = map.findIndex(([node, i]) => {
    if (node === range.startContainer) return i >= range.startOffset
    return !!(range.startContainer.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING)
  })
  if (at < 0) return 0
  let occ = 0
  let i = flat.indexOf(k)
  while (i >= 0 && i < at) { occ++; i = flat.indexOf(k, i + 1) }
  return i === at ? occ : 0
}

function rangesFor(texts: { id: string; text: string; occ?: number }[]) {
  const out = new Map<string, Range>()
  if (!texts.length) return out
  const { flat, map } = flatten()
  for (const p of texts) {
    const k = squash(p.text)
    if (!k) continue
    let at = flat.indexOf(k)
    for (let c = 0; c < (p.occ || 0) && at >= 0; c++) {
      const nx = flat.indexOf(k, at + 1)
      if (nx < 0) break
      at = nx
    }
    if (at < 0) continue
    const [sn, so] = map[at]
    const [en, eo] = map[at + k.length - 1]
    const r = document.createRange()
    r.setStart(sn, so)
    r.setEnd(en, eo + 1)
    out.set(p.id, r)
  }
  return out
}

function paint() {
  const H = (window as any).Highlight
  const reg = (CSS as any).highlights
  if (!H || !reg) return
  if (!isArticle.value) { reg.delete('dt-saved'); return }
  const ranges = rangesFor(passagesOf(path.value))
  reg.set('dt-saved', new H(...ranges.values()))
}
const repaintSoon = () => nextTick(() => setTimeout(paint, 120))

/** 从收藏页点“回到原文”时，地址带 #dt-p=编号，滚动到那一段 */
function jumpIfAsked() {
  const m = location.hash.match(/^#dt-p=([\w]+)/)
  if (!m) return
  if (rel.value.endsWith('read.md') && !reader.value) return   // 原典阅读页：等正文载入后再跳
  const p = passages.value.find((x) => x.id === m[1])
  history.replaceState(null, '', location.pathname + location.search)
  if (!p) return
  setTimeout(() => {
    const r = rangesFor([p]).get(p.id)
    const el = r?.startContainer.parentElement
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    else flash(T('原文已修订，找不到这一段了', '原文已修訂，找不到這一段了'))
  }, 300)
}

onMounted(() => {
  watchScript()
  loadPassages()
  window.addEventListener('dt-reader', onReader)
  document.addEventListener('selectionchange', later)
  document.addEventListener('pointerup', later)
  repaintSoon()
  jumpIfAsked()
})
onBeforeUnmount(() => {
  window.removeEventListener('dt-reader', onReader)
  document.removeEventListener('selectionchange', later)
  document.removeEventListener('pointerup', later)
})
watch(() => route.path, () => { reader.value = null })
watch(path, () => { btn.value = null; card.value = null; repaintSoon(); setTimeout(jumpIfAsked, 200) })
watch(isTrad, () => setTimeout(paint, 300))   // 简繁切换后文字变了，重新找一次
watch(passages, repaintSoon, { deep: true })
</script>

<template>
  <Teleport to="body">
    <div
      v-if="btn"
      class="dt-selbtns"
      :style="{ top: btn.top + 'px', left: btn.left + 'px' }"
      @pointerdown.prevent
      @mousedown.prevent
    >
      <button v-if="btn.bo" class="dt-selbtn" type="button" @click="translate">
        <i class="dt-ico ico-translate" aria-hidden="true"></i>
        <span>{{ T('机器翻译', '機器翻譯') }}</span>
      </button>
      <button class="dt-selbtn" :class="{ on: btn.existing }" type="button" @click="onClick">
        <i class="dt-ico" :class="btn.existing ? 'ico-unmark' : 'ico-mark'" aria-hidden="true"></i>
        <span>{{ btn.existing ? T('取消划线', '取消劃線') : T('划线收藏', '劃線收藏') }}</span>
      </button>
    </div>

    <transition name="dt-fade">
      <section v-if="card" class="dt-trcard" role="dialog" :aria-label="T('机器翻译', '機器翻譯')">
        <button class="dt-trclose" type="button" :aria-label="T('关闭', '關閉')" @click="closeCard">×</button>
        <p class="dt-trsrc dt-bo">{{ card.source }}</p>
        <p v-if="card.loading" class="dt-trwait">{{ T('正在翻译……（长句可能要几十秒，请稍候）', '正在翻譯……（長句可能要幾十秒，請稍候）') }}</p>
        <p v-else-if="card.error" class="dt-trerr">{{ card.error }}
          <button class="dt-tool dt-retry" type="button" @click="retryCard">{{ T('再试一次', '再試一次') }}</button>
        </p>
        <template v-else>
          <p class="dt-trout">{{ card.text }}</p>
          <div class="dt-trops">
            <span class="dt-trnote">{{ T('机器翻译，仅供参考 · Dharmamitra / MITRA', '機器翻譯，僅供參考 · Dharmamitra / MITRA') }}</span>
            <button class="dt-tool small" type="button" @click="copyCard">{{ copied ? T('已复制', '已複製') : T('复制', '複製') }}</button>
            <button class="dt-tool small primary" type="button" :disabled="cardSaved" @click="saveCard">
              {{ cardSaved ? T('已收藏', '已收藏') : T('收藏原文与译文', '收藏原文與譯文') }}
            </button>
          </div>
        </template>
      </section>
    </transition>

    <transition name="dt-fade">
      <div v-if="toast" class="dt-toast">
        {{ toast }}
        <a v-if="!btn" :href="withBase('/saved')">{{ T('查看', '查看') }}</a>
      </div>
    </transition>
  </Teleport>
</template>
