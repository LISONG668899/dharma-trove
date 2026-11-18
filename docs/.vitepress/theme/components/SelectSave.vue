<script setup lang="ts">
// 划线收藏：读者在文章正文里选中一段文字，选区下方出现“划线收藏”按钮；
// 收藏过的段落以后再打开这篇文章，会自动显示金色下划线。
// 选中一段已经划过线的文字，按钮变成“取消划线”。
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useData, useRoute, withBase } from 'vitepress'
import {
  passages, loadPassages, addPassage, removePassage, findPassage, passagesOf,
  normPath, squash, isTrad, watchScript, T
} from '../saved'

const route = useRoute()
const { page, frontmatter } = useData()
const CATS = ['唯识', '中观', '华严', '禅宗', '净土', '大手印', '大圆满', '综合']
const rel = computed(() => page.value.relativePath || '')
const cat = computed(() => rel.value.split('/')[0])
const isArticle = computed(() => CATS.includes(cat.value) && !rel.value.endsWith('index.md'))
const path = computed(() => normPath(route.path))
const title = computed(() => frontmatter.value.title || page.value.title || '')

const btn = ref<{ top: number; left: number; existing: string | null } | null>(null)
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
  const half = 70
  btn.value = {
    top: r.bottom + window.scrollY + 12,
    left: Math.min(Math.max(r.left + r.width / 2 + window.scrollX, half + 8), window.innerWidth - half - 8),
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
  const p = passages.value.find((x) => x.id === m[1])
  history.replaceState(null, '', location.pathname)
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
  document.addEventListener('selectionchange', later)
  document.addEventListener('pointerup', later)
  repaintSoon()
  jumpIfAsked()
})
onBeforeUnmount(() => {
  document.removeEventListener('selectionchange', later)
  document.removeEventListener('pointerup', later)
})
watch(path, () => { btn.value = null; repaintSoon(); setTimeout(jumpIfAsked, 200) })
watch(isTrad, () => setTimeout(paint, 300))   // 简繁切换后文字变了，重新找一次
watch(passages, repaintSoon, { deep: true })
</script>

<template>
  <Teleport to="body">
    <button
      v-if="btn"
      class="dt-selbtn"
      :class="{ on: btn.existing }"
      type="button"
      :style="{ top: btn.top + 'px', left: btn.left + 'px' }"
      @pointerdown.prevent
      @mousedown.prevent
      @click="onClick"
    >
      <i class="dt-ico" :class="btn.existing ? 'ico-unmark' : 'ico-mark'" aria-hidden="true"></i>
      <span>{{ btn.existing ? T('取消划线', '取消劃線') : T('划线收藏', '劃線收藏') }}</span>
    </button>
    <transition name="dt-fade">
      <div v-if="toast" class="dt-toast">
        {{ toast }}
        <a v-if="!btn" :href="withBase('/saved')">{{ T('查看', '查看') }}</a>
      </div>
    </transition>
  </Teleport>
</template>
