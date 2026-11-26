<script setup lang="ts">
// 乾隆大藏经阅读页：/乾隆大藏经/read?t=部号&p=分册
// 正文从 /canon/qianlong/<部号>/<分册>.json 读取（由 scripts/qianlong_build.py 自动生成）。
// 一部经太长时分成几册（如《大般若经》每十卷一册），只载入当前这一册，手机上也不卡。
// 正文是简体；读者切到繁体时，载入后再整体转成繁体，和网站其他页面一致。
// 每次显示完成后发出 dt-reader 事件，让“划线收藏”知道当前是哪部经、哪一册。
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { withBase } from 'vitepress'
import { T } from '../saved'

const NAME = '乾隆大藏经'

interface Entry { t: string; no: number; title: string; juan: string; by: string; sec: string; parts: string[] }
type Block = [string, string]
const entry = ref<Entry | null>(null)
const blocks = ref<Block[]>([])
const part = ref(1)
const error = ref('')
const loading = ref(true)
const root = ref<HTMLElement | null>(null)

let catalogP: Promise<Entry[]> | null = null
const catalog = () => (catalogP ||= fetch(withBase('/canon/qianlong/catalog.json')).then((r) => r.json()))
const total = computed(() => entry.value?.parts.length || 0)

// 本册里的各卷，供“跳到某卷”
const juans = computed(() => blocks.value.map((b, i) => ({ b, i })).filter((x) => x.b[0] === 'j'))
const juanShort = (s: string) => {
  const m = s.match(/卷(第*[一二三四五六七八九十百千零〇]+(之?[上中下])?|[上中下])/)
  return m ? m[0].replace(/第+/, '第') : s
}

function readQuery() {
  const q = new URLSearchParams(location.search)
  return { t: q.get('t') || '', p: Math.max(1, parseInt(q.get('p') || '1', 10) || 1) }
}

/* ---------- 简繁 ---------- */
let s2t: ((s: string) => string) | null = null
async function toTradIfNeeded() {
  if (document.documentElement.getAttribute('data-script') !== 'traditional' || !root.value) return
  if (!s2t) {
    const OpenCC: any = await import('opencc-js')
    s2t = OpenCC.Converter({ from: 'cn', to: 'tw' })
  }
  const walker = document.createTreeWalker(root.value, NodeFilter.SHOW_TEXT)
  let n: Node | null
  while ((n = walker.nextNode())) {
    const t = n as Text
    if (t.data.trim()) t.data = s2t!(t.data)
  }
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
    const r = await fetch(withBase(`/canon/qianlong/${encodeURIComponent(t)}/${p}.json`))
    if (!r.ok) throw new Error('nf')
    const d = await r.json()
    entry.value = e
    part.value = p
    blocks.value = d.blocks
    if (push) history.pushState(null, '', `${location.pathname}?t=${encodeURIComponent(t)}&p=${p}`)
    document.title = `${e.title} · ${NAME}`
    await nextTick()
    await toTradIfNeeded()
    window.dispatchEvent(new CustomEvent('dt-reader', {
      detail: {
        path: decodeURIComponent(location.pathname).replace(/\.html$/, '') + `?t=${t}&p=${p}`,
        title: e.title + (e.parts.length > 1 ? `（${e.parts[p - 1]}）` : ''),
        cat: NAME,
        src: ''
      }
    }))
  } catch {
    error.value = T('找不到这一部经，请从目录重新进入', '找不到這一部經，請從目錄重新進入')
  } finally {
    loading.value = false
  }
}

function go(p: number) {
  if (!entry.value || p < 1 || p > total.value || p === part.value) return
  load(true, entry.value.t, p).then(() => window.scrollTo({ top: 0 }))
}
function jump(i: number) {
  const el = document.getElementById(`ql-${i}`)
  if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 80, behavior: 'smooth' })
}
const onPop = () => load(false)

onMounted(() => { load(false); window.addEventListener('popstate', onPop) })
onBeforeUnmount(() => window.removeEventListener('popstate', onPop))
</script>

<template>
  <div ref="root" class="dt-reader dt-ql-reader">
    <p class="dt-crumb">
      <a :href="withBase(`/${NAME}/`)">{{ NAME }}</a>
      <template v-if="entry">
        <span> › </span>
        <a :href="withBase(`/${NAME}/${entry.sec}`)">{{ entry.sec }}</a>
      </template>
    </p>

    <p v-if="error" class="dt-reader-err">{{ error }}</p>

    <template v-else-if="entry">
      <h1 class="dt-ql-title">{{ entry.title }}</h1>
      <div class="dt-reader-meta">
        <span>第{{ entry.no }}部</span>
        <span v-if="entry.juan">{{ entry.juan }}</span>
        <span v-if="entry.by">{{ entry.by }}</span>
      </div>
      <div v-if="total > 1" class="dt-reader-meta dt-ql-pickrow">
        <span class="dt-reader-pick">
          {{ T('分册', '分冊') }}
          <select :value="part" @change="go(+($event.target as HTMLSelectElement).value)">
            <option v-for="(pt, i) in entry.parts" :key="i" :value="i + 1">{{ i + 1 }}（{{ pt }}）</option>
          </select>
          {{ T('共', '共') }} {{ total }} {{ T('册', '冊') }}
        </span>
      </div>
      <nav v-if="juans.length > 1" class="dt-ql-juans">
        <a v-for="x in juans" :key="x.i" href="javascript:void 0" @click.prevent="jump(x.i)">{{ juanShort(x.b[1]) }}</a>
      </nav>

      <div class="dt-ql-body" :class="{ dim: loading }">
        <template v-for="(b, i) in blocks" :key="part + '-' + i">
          <h2 v-if="b[0] === 'j'" :id="`ql-${i}`" class="dt-ql-juan">{{ b[1] }}</h2>
          <h3 v-else-if="b[0] === 'h'" class="dt-ql-h">{{ b[1] }}</h3>
          <p v-else-if="b[0] === 'b'" class="dt-ql-by">{{ b[1] }}</p>
          <p v-else-if="b[0] === 'v'" class="dt-ql-v">{{ b[1] }}</p>
          <p v-else-if="b[0] === 'k'" class="dt-ql-k">{{ b[1] }}</p>
          <p v-else class="dt-ql-p">{{ b[1] }}</p>
        </template>
      </div>

      <nav v-if="total > 1" class="dt-reader-nav">
        <button class="dt-tool" type="button" :disabled="part <= 1" @click="go(part - 1)">‹ {{ T('上一册', '上一冊') }}</button>
        <span>{{ part }} / {{ total }}</span>
        <button class="dt-tool" type="button" :disabled="part >= total" @click="go(part + 1)">{{ T('下一册', '下一冊') }} ›</button>
      </nav>
    </template>

    <p v-else class="dt-reader-wait">{{ T('载入中……', '載入中……') }}</p>
  </div>
</template>
