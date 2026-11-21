// ============================================================
// 划线收藏（不注册、不上传）：读者在文章里选中一段文字，点“划线收藏”，
// 这一段就存在读者自己浏览器的 localStorage 里。
// 每条：{ id, path, title, cat, text, savedAt }
// 换手机、清除浏览器数据会丢失——这是“不收集读者信息”的代价，
// 所以收藏页提供导出（PDF / Word / TXT），读者可以自己留一份。
// ============================================================
import { ref } from 'vue'

export interface Passage {
  id: string
  path: string
  title: string
  cat: string
  text: string
  occ?: number      // 同样文字在文中出现多次时，划的是第几处（从 0 起）
  tr?: string       // 藏文段落的机器译文（只有在原典里“收藏原文与译文”时才有）
  savedAt: number
}

const KEY = 'dt-passages'
export const passages = ref<Passage[]>([])

export function loadPassages() {
  try {
    const raw = localStorage.getItem(KEY)
    passages.value = raw ? JSON.parse(raw) : []
  } catch {
    passages.value = []
  }
}

function persist() {
  try { localStorage.setItem(KEY, JSON.stringify(passages.value)) } catch {}
}

export function normPath(p: string) {
  try { p = decodeURIComponent(p) } catch {}
  return p.replace(/\.html$/, '').replace(/[#?].*$/, '')
}

/** 把文字压成一行、去掉多余空白，用来比对与查找 */
export const squash = (s: string) => s.replace(/\s+/g, '')

export function findPassage(path: string, text: string) {
  path = normPath(path)
  const k = squash(text)
  return passages.value.find((p) => p.path === path && squash(p.text) === k)
}

export function addPassage(path: string, title: string, cat: string, text: string, occ = 0, tr?: string): Passage {
  path = normPath(path)
  const old = findPassage(path, text)
  if (old) {
    if (tr && old.tr !== tr) { old.tr = tr; passages.value = [...passages.value]; persist() }
    return old
  }
  const p: Passage = { id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), path, title, cat, text, occ, tr, savedAt: Date.now() }
  passages.value = [p, ...passages.value]
  persist()
  return p
}

export function removePassage(id: string) {
  passages.value = passages.value.filter((p) => p.id !== id)
  persist()
}

export function passagesOf(path: string) {
  path = normPath(path)
  return passages.value.filter((p) => p.path === path)
}

/** 按文章分组（文章按最近一次收藏排序，组内按原文先后——这里用收藏时间近似） */
export function grouped() {
  const map = new Map<string, { path: string; title: string; cat: string; items: Passage[]; last: number }>()
  for (const p of passages.value) {
    let g = map.get(p.path)
    if (!g) { g = { path: p.path, title: p.title, cat: p.cat, items: [], last: 0 }; map.set(p.path, g) }
    g.items.push(p)
    g.last = Math.max(g.last, p.savedAt)
  }
  const groups = [...map.values()].sort((a, b) => b.last - a.last)
  groups.forEach((g) => g.items.sort((a, b) => a.savedAt - b.savedAt))
  return groups
}

/* ---------- 简繁：跟随顶部“简/繁”按钮（ConvertToggle 在 <html> 上打的 data-script 标记） ---------- */
export const isTrad = ref(false)
let watching = false
export function watchScript() {
  if (typeof document === 'undefined') return
  const read = () => (isTrad.value = document.documentElement.getAttribute('data-script') === 'traditional')
  read()
  try { if (localStorage.getItem('dharmatrove-script') === 'traditional') isTrad.value = true } catch {}
  if (watching) return
  watching = true
  new MutationObserver(read).observe(document.documentElement, { attributes: true, attributeFilter: ['data-script'] })
}
/** 界面文字：简体、繁体各写一份，按当前模式取 */
export const T = (s: string, t: string) => (isTrad.value ? t : s)
