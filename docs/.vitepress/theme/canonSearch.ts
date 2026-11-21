// ============================================================
// 藏文原典全文检索（德格版《甘珠尔》《丹珠尔》）
// 藏文没有空格，通用的搜索工具（Pagefind）切不开词，所以单独做：
//   1. scripts/canon_build.py 生成按音节的倒排索引：/canon/<集>/search/0–255.json
//   2. 搜索时把查询切成音节，只下载这几个音节所在的索引小文件，求出同时含有全部音节的正文分段
//   3. 再逐段下载正文，逐字核对整句是否连续出现，取出前后文作摘要
// 另外先在经目里找经名含有查询的经论，排在最前面。
// ============================================================
import { withBase } from 'vitepress'

export interface Hit { url: string; title: string; excerpt: string }

const COLLS = [
  { key: 'kangyur', zh: '甘珠尔' },
  { key: 'tengyur', zh: '丹珠尔' }
] as const
const NSHARD = 256
const SPLIT = /[་༌།-༔༁-༊༴༺-༽\s]+/
const isSyl = (x: string) => /[ཀ-ྼ]/.test(x)

export const hasTibetan = (s: string) => /[ༀ-࿿]/.test(s)
const squash = (s: string) => s.replace(/\s+/g, '')
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

function shardOf(syl: string) {
  let h = 0x811c9dc5
  for (let i = 0; i < syl.length; i++) {
    h ^= syl.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h % NSHARD
}

const cache = new Map<string, Promise<any>>()
const getJSON = (u: string) => {
  if (!cache.has(u)) cache.set(u, fetch(withBase(u)).then((r) => { if (!r.ok) throw new Error(u); return r.json() }))
  return cache.get(u)!
}

function decodePost(s: string): number[] {
  const out: number[] = []
  let prev = 0
  for (const x of s.split(',')) { prev += parseInt(x, 36); out.push(prev) }
  return out
}

function intersect(lists: number[][]) {
  lists.sort((a, b) => a.length - b.length)
  let cur = lists[0]
  for (const l of lists.slice(1)) {
    const set = new Set(l)
    cur = cur.filter((x) => set.has(x))
  }
  return cur
}

/** 在一段文字里找查询（忽略空白），返回带 <mark> 的前后文 */
function excerptOf(text: string, q: string): string | null {
  const map: number[] = []
  let flat = ''
  for (let i = 0; i < text.length; i++) if (!/\s/.test(text[i])) { flat += text[i]; map.push(i) }
  const at = flat.indexOf(q)
  if (at < 0) return null
  const s = map[at], e = map[at + q.length - 1] + 1
  const a = Math.max(0, s - 70), b = Math.min(text.length, e + 70)
  return (a > 0 ? '…' : '') + esc(text.slice(a, s)) + '<mark>' + esc(text.slice(s, e)) + '</mark>' + esc(text.slice(e, b)) + (b < text.length ? '…' : '')
}

export interface CanonSearch {
  titleHits: Hit[]
  candidates: number
  more: (n: number) => Promise<Hit[]>
  done: () => boolean
}

export async function canonSearch(raw: string): Promise<CanonSearch> {
  const q = squash(raw).replace(/^[་།]+|[་།༔]+$/g, '')
  const syls = [...new Set(raw.split(SPLIT).filter(isSyl))]
  const titleHits: Hit[] = []
  const queue: { coll: (typeof COLLS)[number]; t: string; p: number; title: string }[] = []

  for (const coll of COLLS) {
    const cat: any[] = await getJSON(`/canon/${coll.key}/catalog.json`)
    const byT = new Map(cat.map((e) => [e.t, e]))
    for (const e of cat) {
      if (squash(e.title).includes(q)) {
        titleHits.push({
          url: withBase(`/${coll.zh}/read?t=${encodeURIComponent(e.t)}&p=1`),
          title: e.title,
          excerpt: `${coll.zh}${e.toh ? ' · Toh ' + e.toh : ''} · ${esc(e.sec)}`
        })
      }
    }
    if (!syls.length) continue
    const parts: [string, number][] = await getJSON(`/canon/${coll.key}/search/parts.json`)
    const lists = await Promise.all(syls.map(async (s) => {
      const sh = await getJSON(`/canon/${coll.key}/search/${shardOf(s)}.json`)
      return sh[s] ? decodePost(sh[s]) : []
    }))
    if (lists.some((l) => !l.length)) continue
    for (const pid of intersect(lists)) {
      const [t, p] = parts[pid]
      queue.push({ coll, t, p, title: byT.get(t)?.title || t })
    }
  }

  let i = 0
  return {
    titleHits,
    candidates: queue.length,
    done: () => i >= queue.length,
    async more(n: number) {
      const out: Hit[] = []
      while (out.length < n && i < queue.length) {
        const batch = queue.slice(i, i + 16)
        i += batch.length
        const res = await Promise.all(batch.map(async (c) => {
          try {
            const d = await getJSON(`/canon/${c.coll.key}/${c.t}/${c.p}.json`)
            for (const [label, text] of d.paras as [string, string][]) {
              const ex = excerptOf(text, q)
              if (ex) {
                return {
                  url: withBase(`/${c.coll.zh}/read?t=${encodeURIComponent(c.t)}&p=${c.p}&q=${encodeURIComponent(q)}`),
                  title: c.title,
                  excerpt: `<span class="cs-where">${c.coll.zh} · ${esc(label)}</span>${ex}`
                } as Hit
              }
            }
          } catch {}
          return null
        }))
        for (const r of res) if (r) out.push(r)
      }
      return out
    }
  }
}
