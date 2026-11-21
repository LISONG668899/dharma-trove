<script setup lang="ts">
// 藏文原典阅读页：/甘珠尔/read?t=经号&p=分段
// 正文从 /canon/<kangyur|tengyur>/<经号>/<分段>.json 读取（由 scripts/canon_build.py 自动生成），
// 每一面（如“ཀ 1b”）排成一段，段首小字标出函与叶码。
// 切换分段不重新载入整页；每次显示完成后发出 dt-reader 事件，
// 让“划线收藏 / 机器翻译”知道当前是哪部经、哪一段。
import { computed, onBeforeUnmount, onMounted, ref, nextTick } from 'vue'
import { withBase } from 'vitepress'

const props = defineProps<{ coll: 'kangyur' | 'tengyur' }>()
const NAME = { kangyur: { zh: '甘珠尔', bo: 'བཀའ་འགྱུར།' }, tengyur: { zh: '丹珠尔', bo: 'བསྟན་འགྱུར།' } }
const name = computed(() => NAME[props.coll])

interface Entry { t: string; toh: string; title: string; sec: string; parts: [string, string][] }
const entry = ref<Entry | null>(null)
const paras = ref<[string, string][]>([])
const part = ref(1)
const error = ref('')
const loading = ref(true)

let catalogP: Promise<Entry[]> | null = null
const catalog = () => (catalogP ||= fetch(withBase(`/canon/${props.coll}/catalog.json`)).then((r) => r.json()))

const secSlug = (s: string) => s.replace(/[།༎\s]/g, '')
const total = computed(() => entry.value?.parts.length || 0)

function readQuery() {
  const q = new URLSearchParams(location.search)
  return { t: q.get('t') || '', p: Math.max(1, parseInt(q.get('p') || '1', 10) || 1) }
}

async function load(push = false, t?: string, p?: number) {
  const q = readQuery()
  t = t ?? q.t
  p = p ?? q.p
  loading.value = true
  error.value = ''
  try {
    const cat = await catalog()
    const e = cat.find((x) => x.t === t)
    if (!e) throw new Error('nf')
    p = Math.min(p, e.parts.length)
    const r = await fetch(withBase(`/canon/${props.coll}/${encodeURIComponent(t)}/${p}.json`))
    if (!r.ok) throw new Error('nf')
    const d = await r.json()
    entry.value = e
    part.value = p
    paras.value = d.paras
    const url = `${location.pathname}?t=${encodeURIComponent(t)}&p=${p}`
    if (push) history.pushState(null, '', url)   // 翻到别的分段时不再带搜索词
    document.title = `${e.title} · ${name.value.zh}`
    await nextTick()
    setTimeout(markQuery, 60)
    window.dispatchEvent(new CustomEvent('dt-reader', {
      detail: {
        path: decodeURIComponent(location.pathname).replace(/\.html$/, '') + `?t=${t}&p=${p}`,
        title: e.title + (e.parts.length > 1 ? `（${p}/${e.parts.length}）` : ''),
        cat: name.value.zh,
        src: `/canon/${props.coll}/${t}/${p}.json`
      }
    }))
  } catch {
    error.value = '找不到这一部经论，请从目录重新进入'
  } finally {
    loading.value = false
  }
}

/** 从搜索结果进来（地址带 &q=…）：把查询的字在正文里标出来，并滚到第一处 */
function markQuery() {
  const H = (window as any).Highlight, reg = (CSS as any).highlights
  const q = new URLSearchParams(location.search).get('q') || ''
  if (reg) reg.delete('dt-find')
  if (!q) return
  const body = document.querySelector('.dt-reader-body')
  if (!body) return
  const ranges: Range[] = []
  for (const p of body.querySelectorAll('p')) {
    const t = p.firstChild as Text | null
    if (!t || t.nodeType !== 3) continue
    const map: number[] = []
    let flat = ''
    for (let i = 0; i < t.data.length; i++) if (!/\s/.test(t.data[i])) { flat += t.data[i]; map.push(i) }
    let at = flat.indexOf(q)
    while (at >= 0) {
      const r = document.createRange()
      r.setStart(t, map[at]); r.setEnd(t, map[at + q.length - 1] + 1)
      ranges.push(r)
      at = flat.indexOf(q, at + q.length)
    }
  }
  if (H && reg && ranges.length) reg.set('dt-find', new H(...ranges))
  if (ranges.length) {
    const el = ranges[0].startContainer.parentElement
    const top = ranges[0].getBoundingClientRect().top + window.scrollY - window.innerHeight / 3
    window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
    void el
  }
}

function go(p: number) {
  if (!entry.value || p < 1 || p > total.value || p === part.value) return
  load(true, entry.value.t, p).then(() => window.scrollTo({ top: 0 }))
}
const onPop = () => load(false)

onMounted(() => { load(false); window.addEventListener('popstate', onPop) })
onBeforeUnmount(() => window.removeEventListener('popstate', onPop))
</script>

<template>
  <!-- translate="no"：告诉浏览器和谷歌翻译这里的藏文不必翻译，少弹出谷歌翻译按钮 -->
  <div class="dt-reader notranslate" translate="no">
    <p class="dt-crumb">
      <a :href="withBase(`/${name.zh}/`)">{{ name.zh }}</a>
      <template v-if="entry">
        <span> › </span>
        <a :href="withBase(`/${name.zh}/${secSlug(entry.sec)}`)" class="dt-bo">{{ entry.sec }}</a>
      </template>
    </p>

    <p v-if="error" class="dt-reader-err">{{ error }}</p>

    <template v-else-if="entry">
      <h1 class="dt-reader-title dt-bo">{{ entry.title }}</h1>
      <div class="dt-reader-meta">
        <span v-if="entry.toh">Toh {{ entry.toh }}</span>
        <span v-if="total > 1" class="dt-reader-pick">
          第
          <select :value="part" @change="go(+($event.target as HTMLSelectElement).value)">
            <option v-for="(pt, i) in entry.parts" :key="i" :value="i + 1">{{ i + 1 }}（{{ pt[1] }}）</option>
          </select>
          段，共 {{ total }} 段
        </span>
      </div>

      <div class="dt-reader-body" :class="{ dim: loading }">
        <!-- 函与叶码用 CSS ::before 显示，不进入选中的文字，翻译和收藏只取经文本身 -->
        <p v-for="(pa, i) in paras" :key="part + '-' + i" class="dt-bo-p" :data-f="pa[0]">{{ pa[1] }}</p>
      </div>

      <nav v-if="total > 1" class="dt-reader-nav">
        <button class="dt-tool" type="button" :disabled="part <= 1" @click="go(part - 1)">‹ 上一段</button>
        <span>{{ part }} / {{ total }}</span>
        <button class="dt-tool" type="button" :disabled="part >= total" @click="go(part + 1)">下一段 ›</button>
      </nav>
    </template>

    <p v-else class="dt-reader-wait">载入中……</p>
  </div>
</template>
