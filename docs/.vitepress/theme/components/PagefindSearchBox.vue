<script setup lang="ts">
// 藏汉佛教精华 · 站内搜索框（Pagefind）
// - 替换 VitePress 自带搜索框；顶部搜索图标保持不变
// - 输入时不弹出任何结果，点“搜索”或按回车/手机键盘“搜索”键才搜
// - 中文关键词按整词精确匹配
// - 跟随网站顶部“简/繁”按钮：繁体模式下界面与结果显示繁体，输入繁体也能搜到
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { useRouter, withBase } from 'vitepress'

const emit = defineEmits<{ (e: 'close'): void }>()
const router = useRouter()

const PAGE_SIZE = 20

const el = shallowRef<HTMLElement>()
const input = ref<HTMLInputElement>()
const query = ref('')
const loading = ref(false)
const searched = ref(false)
const failed = ref(false)
const total = ref(0)
const items = ref<{ url: string; title: string; excerpt: string }[]>([])
const selected = ref(-1)

let allResults: any[] = []
let shown = 0
let seq = 0

/* ---------- 简繁 ---------- */
const isTrad = ref(false)
try {
  isTrad.value = localStorage.getItem('dharmatrove-script') === 'traditional'
} catch (e) {}
const T = (s: string, t: string) => (isTrad.value ? t : s)

let s2t: ((x: string) => string) | null = null
let t2s: ((x: string) => string) | null = null
async function loadOpenCC() {
  if (s2t) return
  const OpenCC: any = await import('opencc-js')
  s2t = OpenCC.Converter({ from: 'cn', to: 'tw' })
  t2s = OpenCC.Converter({ from: 'tw', to: 'cn' })
}
function convertToTrad() {
  if (!isTrad.value || !s2t || !el.value) return
  const w = document.createTreeWalker(el.value, NodeFilter.SHOW_TEXT)
  let n: Node | null
  while ((n = w.nextNode())) {
    const t = n as Text
    if (/[一-鿿]/.test(t.data)) {
      const v = s2t(t.data)
      if (v !== t.data) t.data = v
    }
  }
}

/* ---------- Pagefind ---------- */
let pagefind: any = null
let pagefindLoading: Promise<any> | null = null
function loadPagefind() {
  if (pagefind) return Promise.resolve(pagefind)
  if (!pagefindLoading) {
    const url = withBase('/pagefind/pagefind.js')
    pagefindLoading = import(/* @vite-ignore */ url)
      .then(async (m) => {
        await m.options({ excerptLength: 36 })
        m.init()
        pagefind = m
        return m
      })
      .catch((e) => {
        pagefindLoading = null
        throw e
      })
  }
  return pagefindLoading
}

// 中文/藏文关键词加引号做整词精确匹配
function exact(w: string) {
  w = w.replace(/"/g, '')
  return /[㐀-鿿ༀ-࿿]/.test(w) ? `"${w}"` : w
}

// 空格分开的多个词：逐词精确搜索，只保留同时包含全部词的文章，按综合相关度排序
async function searchAll(pf: any, q: string) {
  const words = q.split(/\s+/).filter(Boolean)
  if (words.length === 1) return (await pf.search(exact(words[0]))).results
  const lists = await Promise.all(words.map(async (w) => (await pf.search(exact(w))).results))
  const score = new Map<string, number>()
  for (const r of lists[0]) score.set(r.id, r.score)
  for (const list of lists.slice(1)) {
    const ids = new Set(list.map((r: any) => r.id))
    for (const id of [...score.keys()]) if (!ids.has(id)) score.delete(id)
    for (const r of list) if (score.has(r.id)) score.set(r.id, score.get(r.id)! + r.score)
  }
  return lists[0]
    .filter((r: any) => score.has(r.id))
    .sort((a: any, b: any) => score.get(b.id)! - score.get(a.id)!)
}

function cleanTitle(t: string) {
  return (t || '')
    .replace(/[​‌‍﻿]/g, '')
    .replace(/\s*\|\s*藏汉佛教精华\s*$/, '')
    .trim()
}

async function doSearch() {
  const raw = query.value.trim()
  if (!raw) return
  input.value?.blur()
  const my = ++seq
  loading.value = true
  searched.value = true
  failed.value = false
  items.value = []
  total.value = 0
  selected.value = -1
  try {
    let q = raw
    if (isTrad.value) {
      await loadOpenCC()
      q = t2s!(q)
    }
    const pf = await loadPagefind()
    const res = await searchAll(pf, q)
    if (my !== seq) return
    allResults = res
    total.value = allResults.length
    shown = 0
    await more()
    selected.value = items.value.length ? 0 : -1
  } catch (e) {
    if (my === seq) failed.value = true
  } finally {
    if (my === seq) {
      loading.value = false
      await nextTick()
      convertToTrad()
    }
  }
}

async function more() {
  const slice = allResults.slice(shown, shown + PAGE_SIZE)
  shown += slice.length
  const data = await Promise.all(slice.map((r) => r.data()))
  items.value = items.value.concat(
    data.map((d: any) => ({
      url: d.url,
      title: cleanTitle(d.meta?.title || d.url),
      excerpt: d.excerpt
    }))
  )
  await nextTick()
  convertToTrad()
}

function go(url: string) {
  router.go(url)
  emit('close')
}

function reset() {
  seq++
  query.value = ''
  items.value = []
  total.value = 0
  searched.value = false
  failed.value = false
  loading.value = false
  input.value?.focus()
}

// 改动关键词后清空旧结果，等再次点“搜索”
function onInput() {
  if (searched.value) {
    seq++
    items.value = []
    total.value = 0
    searched.value = false
    loading.value = false
  }
}

/* ---------- 键盘 ---------- */
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    emit('close')
  } else if (e.key === 'ArrowDown' && items.value.length) {
    e.preventDefault()
    selected.value = (selected.value + 1) % items.value.length
    scrollSel()
  } else if (e.key === 'ArrowUp' && items.value.length) {
    e.preventDefault()
    selected.value = (selected.value - 1 + items.value.length) % items.value.length
    scrollSel()
  } else if (e.key === 'Enter' && !e.isComposing && e.target !== input.value) {
    const it = items.value[selected.value]
    if (it && !(e.target instanceof HTMLButtonElement)) {
      e.preventDefault()
      go(it.url)
    }
  }
}
// 输入框里按回车：关键词没变且已有结果 → 打开选中的结果；否则执行搜索
function onSubmit() {
  if (searched.value && !loading.value && items.value.length && document.activeElement === input.value) {
    const it = items.value[selected.value]
    if (it) return go(it.url)
  }
  doSearch()
}
function scrollSel() {
  nextTick(() => el.value?.querySelector('.pf-item.selected')?.scrollIntoView({ block: 'nearest' }))
}

/* ---------- 打开 / 关闭 ---------- */
let prevOverflow = ''
function onPop() {
  emit('close')
}
onMounted(() => {
  prevOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  window.addEventListener('keydown', onKeydown)
  window.history.pushState(null, '', null)
  window.addEventListener('popstate', onPop)
  nextTick(() => input.value?.focus())
  loadPagefind().catch(() => {})
  if (isTrad.value) loadOpenCC().then(() => nextTick(convertToTrad))
})
onBeforeUnmount(() => {
  document.body.style.overflow = prevOverflow
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('popstate', onPop)
})

const buttonLabel = computed(() => T('搜索', '搜尋'))
</script>

<template>
  <Teleport to="body">
    <div ref="el" class="pf-box" role="dialog" aria-modal="true">
      <div class="pf-backdrop" @click="emit('close')" />
      <div class="pf-shell">
        <form class="pf-bar" @submit.prevent="onSubmit">
          <button type="button" class="pf-back" :title="T('关闭', '關閉')" @click="emit('close')">
            <span class="vpi-arrow-left pf-icon" />
          </button>
          <span class="vpi-search pf-icon pf-search-icon" />
          <input
            ref="input"
            v-model="query"
            class="pf-input"
            type="search"
            enterkeyhint="search"
            autocomplete="off"
            autocorrect="off"
            autocapitalize="off"
            spellcheck="false"
            maxlength="64"
            @input="onInput"
          />
          <button class="pf-submit" type="submit">{{ buttonLabel }}</button>
          <button
            type="button"
            class="pf-clear"
            :disabled="!query"
            :title="T('清除', '清除')"
            @click="reset"
          >
            <span class="vpi-delete pf-icon" />
          </button>
        </form>

        <div v-if="searched" class="pf-results">
          <div v-if="loading" class="pf-msg">{{ T('正在搜索……', '正在搜尋……') }}</div>
          <div v-else-if="failed" class="pf-msg">
            {{ T('搜索暂时不可用，请稍后再试', '搜尋暫時不可用，請稍後再試') }}
          </div>
          <div v-else-if="!total" class="pf-msg">
            {{ T('没有找到包含', '沒有找到包含') }}“<strong>{{ query.trim() }}</strong>”{{ T('的文章', '的文章') }}
          </div>
          <template v-else>
            <div class="pf-count">{{ T('共找到', '共找到') }} {{ total }} {{ T('篇', '篇') }}</div>
            <ul class="pf-list">
              <li v-for="(it, i) in items" :key="it.url">
                <a
                  class="pf-item"
                  :class="{ selected: i === selected }"
                  :href="it.url"
                  @click.prevent="go(it.url)"
                  @mouseenter="selected = i"
                >
                  <div class="pf-title">{{ it.title }}</div>
                  <div class="pf-excerpt" v-html="it.excerpt" />
                </a>
              </li>
            </ul>
            <button v-if="items.length < total" type="button" class="pf-more" @click="more">
              {{ T('显示更多', '顯示更多') }}（{{ items.length }} / {{ total }}）
            </button>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.pf-box {
  /* 网站主色：金色 */
  --pf-gold: #b8891f;
  --pf-gold-hover: #9c7419;
  --pf-gold-line: #c9982f;
  --pf-mark-bg: rgba(212, 160, 23, 0.28);
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
}
.pf-backdrop {
  position: absolute;
  inset: 0;
  background: var(--vp-backdrop-bg-color);
}
.pf-shell {
  position: relative;
  margin: auto;
  width: min(100vw - 60px, 860px);
  max-height: min(100vh - 128px, 860px);
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: var(--vp-local-search-bg, var(--vp-c-bg));
  border-radius: 10px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
}
@media (max-width: 767px) {
  .pf-shell {
    /* 手机：放在屏幕约三成高度处，键盘弹出也不遮挡 */
    margin: 28vh auto auto;
    width: calc(100vw - 24px);
    max-height: 62vh;
  }
}

.pf-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 4px 0 8px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  height: 48px;
  flex-shrink: 0;
}
.pf-bar:focus-within {
  border-color: var(--pf-gold-line);
}
.pf-icon {
  display: block;
  font-size: 18px;
}
.pf-back {
  display: none;
  padding: 8px 4px;
}
.pf-search-icon {
  margin: 0 4px;
  color: var(--vp-c-text-2);
}
@media (max-width: 767px) {
  .pf-back {
    display: block;
  }
  .pf-search-icon {
    display: none;
  }
}
.pf-input {
  flex: 1;
  min-width: 0;
  padding: 6px 8px;
  font-size: 16px;
  background: transparent;
}
.pf-input::-webkit-search-cancel-button {
  -webkit-appearance: none;
  display: none;
}
.pf-submit {
  flex-shrink: 0;
  height: 34px;
  padding: 0 16px;
  border-radius: 5px;
  background: var(--pf-gold);
  color: #fff;
  font-size: 15px;
  letter-spacing: 1px;
}
.pf-submit:hover {
  background: var(--pf-gold-hover);
}
.pf-clear {
  flex-shrink: 0;
  padding: 8px;
  color: var(--vp-c-text-2);
}
.pf-clear:disabled {
  opacity: 0.35;
}

.pf-results {
  overflow-y: auto;
  overscroll-behavior: contain;
}
.pf-msg {
  padding: 18px 8px;
  text-align: center;
  color: var(--vp-c-text-2);
  font-size: 15px;
}
.pf-count {
  padding: 0 4px 8px;
  font-size: 13px;
  color: var(--vp-c-text-3);
}
.pf-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pf-item {
  display: block;
  padding: 10px 12px;
  border: 2px solid var(--vp-c-divider);
  border-radius: 6px;
  color: var(--vp-c-text-1);
  text-decoration: none;
}
.pf-item.selected {
  border-color: var(--pf-gold-line);
}
.pf-title {
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
}
.pf-item.selected .pf-title {
  color: var(--pf-gold);
}
.pf-excerpt {
  margin-top: 4px;
  font-size: 14px;
  line-height: 1.65;
  color: var(--vp-c-text-2);
  word-break: break-all;
}
.pf-excerpt :deep(mark) {
  background: var(--pf-mark-bg);
  color: var(--vp-c-text-1);
  padding: 0;
}
.pf-more {
  display: block;
  margin: 10px auto 2px;
  padding: 6px 18px;
  border: 1px solid var(--pf-gold-line);
  border-radius: 5px;
  color: var(--pf-gold);
  font-size: 14px;
}
.pf-more:hover {
  background: var(--pf-mark-bg);
}
</style>
