<script setup lang="ts">
// 我的收藏：读者在文章里划线收藏的段落，按文章分组；
// 可回到原文、取消划线，也可把全部段落导出为 PDF / Word / TXT。
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { withBase } from 'vitepress'
import { passages, loadPassages, removePassage, grouped, watchScript, T } from '../saved'

const groups = computed(() => { passages.value; return grouped() })
const count = computed(() => passages.value.length)
const menu = ref(false)

const fmt = (t: number) => {
  const d = new Date(t)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const jump = (path: string, id: string) => withBase(path) + '#dt-p=' + id
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const head = () => `${T('藏汉佛教精华 · 我的收藏', '藏漢佛教精華 · 我的收藏')}`
const sub = () => `${fmt(Date.now())}　${T('共', '共')} ${count.value} ${T('段', '段')}　${location.origin}`
const fileBase = () => `DharmaTrove-${T('我的收藏', '我的收藏')}-${fmt(Date.now())}`

function download(blob: Blob, name: string) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = name
  document.body.appendChild(a)
  a.click()
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove() }, 1000)
}

function exportPdf() {
  menu.value = false
  // 打印时只保留段落列表（见 tools.css 里的 @media print），在打印对话框里选“存为 PDF”
  setTimeout(() => window.print(), 50)
}

function exportWord() {
  menu.value = false
  let body = `<h1>${esc(head())}</h1><p class="sub">${esc(sub())}</p>`
  for (const g of groups.value) {
    body += `<h2>${esc(g.title)}</h2><p class="src">${g.cat ? esc(g.cat) + '　' : ''}${esc(location.origin + g.path)}</p>`
    for (const p of g.items) body += `<p class="p">${esc(p.text).replace(/\n/g, '<br>')}</p>`
  }
  const html =
    '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">' +
    `<head><meta charset="utf-8"><title>${esc(head())}</title><style>` +
    'body{font-family:"Songti SC","SimSun","宋体",serif;font-size:12pt;line-height:1.8}' +
    'h1{font-size:18pt;text-align:center}h2{font-size:14pt;margin-top:18pt;border-bottom:1px solid #c9982f}' +
    '.sub{text-align:center;color:#888;font-size:9pt}.src{color:#888;font-size:9pt}' +
    '.p{border-left:3pt solid #c9982f;padding-left:8pt;margin:10pt 0}' +
    `</style></head><body>${body}</body></html>`
  download(new Blob(['﻿' + html], { type: 'application/msword' }), fileBase() + '.doc')
}

function exportTxt() {
  menu.value = false
  let s = `${head()}\n${sub()}\n`
  for (const g of groups.value) {
    s += `\n━━━━━━━━━━\n${g.title}\n${g.cat ? g.cat + '　' : ''}${location.origin + g.path}\n`
    for (const p of g.items) s += `\n${p.text}\n`
  }
  download(new Blob(['﻿' + s.replace(/\r?\n/g, '\r\n')], { type: 'text/plain;charset=utf-8' }), fileBase() + '.txt')
}

function onDocClick(e: MouseEvent) {
  if (!(e.target as HTMLElement).closest('.dt-export')) menu.value = false
}
onMounted(() => { watchScript(); loadPassages(); document.addEventListener('click', onDocClick) })
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <div class="dt-saved">
    <p class="dt-privacy">
      <i class="dt-ico ico-lock" aria-hidden="true"></i>
      {{ T('收藏只保存在您这台设备的浏览器里，本站不收集任何读者信息。换手机或清除浏览器数据后收藏会消失，请记得导出留存。', '收藏只保存在您這台裝置的瀏覽器裡，本站不收集任何讀者資訊。換手機或清除瀏覽器資料後收藏會消失，請記得導出留存。') }}
    </p>

    <p class="dt-how">
      {{ T('阅读任何一篇文章时，用手指或鼠标选中一段文字，选区下方会出现“划线收藏”按钮，点一下，这一段就会画上金色下划线并收进这里；再次选中同一段，可以取消划线。在德格版《甘珠尔》《丹珠尔》的藏文原典里，选中一段藏文还可以先请机器译成白话，再把原文和译文一起收藏。收藏的段落按文章分组，点“回到原文”可以跳回原处，点“导出全部”可以存成 PDF、Word 或纯文本。', '閱讀任何一篇文章時，用手指或滑鼠選中一段文字，選區下方會出現“劃線收藏”按鈕，點一下，這一段就會畫上金色下劃線並收進這裡；再次選中同一段，可以取消劃線。在德格版《甘珠爾》《丹珠爾》的藏文原典裡，選中一段藏文還可以先請機器譯成白話，再把原文和譯文一起收藏。收藏的段落按文章分組，點“回到原文”可以跳回原處，點“導出全部”可以存成 PDF、Word 或純文本。') }}
    </p>

    <p v-if="!count" class="dt-saved-empty">{{ T('还没有收藏的段落', '還沒有收藏的段落') }}</p>

    <template v-else>
      <div class="dt-saved-bar">
        <span>{{ T('共', '共') }} {{ groups.length }} {{ T('篇文章', '篇文章') }} · {{ count }} {{ T('段', '段') }}</span>
        <div class="dt-export">
          <button class="dt-tool primary" :class="{ open: menu }" type="button" :aria-expanded="menu" @click="menu = !menu">
            <i class="dt-ico ico-export" aria-hidden="true"></i>
            <span>{{ T('导出全部', '導出全部') }}</span>
          </button>
          <div v-if="menu" class="dt-menu" role="menu">
            <button type="button" role="menuitem" @click="exportPdf"><b>PDF</b><span>{{ T('打印或存为 PDF', '列印或存為 PDF') }}</span></button>
            <button type="button" role="menuitem" @click="exportWord"><b>Word</b><span>{{ T('下载可编辑文档', '下載可編輯文檔') }}</span></button>
            <button type="button" role="menuitem" @click="exportTxt"><b>TXT</b><span>{{ T('下载纯文本', '下載純文本') }}</span></button>
          </div>
        </div>
      </div>

      <section v-for="g in groups" :key="g.path" class="dt-group">
        <h2 class="dt-group-title">
          <a :href="withBase(g.path)">{{ g.title }}</a>
          <span v-if="g.cat" class="dt-saved-cat">{{ g.cat }}</span>
        </h2>
        <div v-for="p in g.items" :key="p.id" class="dt-passage">
          <p class="dt-passage-text">{{ p.text }}</p>
          <div class="dt-passage-ops">
            <span>{{ fmt(p.savedAt) }}</span>
            <a class="dt-link" :href="jump(p.path, p.id)">{{ T('回到原文', '回到原文') }}</a>
            <button class="dt-link" type="button" @click="removePassage(p.id)">{{ T('取消划线', '取消劃線') }}</button>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
