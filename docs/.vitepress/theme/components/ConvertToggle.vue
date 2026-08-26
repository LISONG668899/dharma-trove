<script setup>
// 简繁切换按钮
// 点击后遍历整个页面 DOM 的文本节点，用 opencc-js 转换简体/繁体
// 用户的选择存在 localStorage，刷新页面后自动记住上次的状态
import { ref, onMounted } from 'vue'

const isTraditional = ref(false)
let converterS2T = null
let converterT2S = null
// 记录每个文本节点的原始简体文字，这样繁体->简体时能无损还原
// 而不是对已经转换过的繁体文字再做一次"繁转简"（避免多次转换造成的偏差累积）
const originalTextMap = new WeakMap()

function collectTextNodes(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      // 跳过代码块、跳过纯空白节点
      const parentTag = node.parentElement?.tagName
      if (parentTag === 'CODE' || parentTag === 'PRE' || parentTag === 'SCRIPT' || parentTag === 'STYLE') {
        return NodeFilter.FILTER_REJECT
      }
      if (!node.textContent || !node.textContent.trim()) {
        return NodeFilter.FILTER_REJECT
      }
      return NodeFilter.FILTER_ACCEPT
    }
  })
  const nodes = []
  let n
  while ((n = walker.nextNode())) nodes.push(n)
  return nodes
}

async function applyConversion(toTraditional) {
  if (typeof window === 'undefined') return
  if (!converterS2T) {
    const OpenCC = await import('opencc-js')
    converterS2T = OpenCC.Converter({ from: 'cn', to: 'tw' })
    converterT2S = OpenCC.Converter({ from: 'tw', to: 'cn' })
  }

  const nodes = collectTextNodes(document.querySelector('#app') || document.body)
  for (const node of nodes) {
    if (toTraditional) {
      if (!originalTextMap.has(node)) {
        originalTextMap.set(node, node.textContent)
      }
      node.textContent = converterS2T(originalTextMap.get(node))
    } else {
      // 优先用记录的原始简体文字还原，没有记录的（比如切换后新渲染的节点）再走繁转简
      node.textContent = originalTextMap.has(node)
        ? originalTextMap.get(node)
        : converterT2S(node.textContent)
    }
  }
}

function setScriptAttr(toTraditional) {
  // 给 <html> 打标记，custom.css 里用这个属性微调繁体模式的行高
  document.documentElement.setAttribute('data-script', toTraditional ? 'traditional' : 'simplified')
}

async function toggle() {
  isTraditional.value = !isTraditional.value
  localStorage.setItem('dharmatrove-script', isTraditional.value ? 'traditional' : 'simplified')
  setScriptAttr(isTraditional.value)
  await applyConversion(isTraditional.value)
}

onMounted(async () => {
  const saved = localStorage.getItem('dharmatrove-script')
  if (saved === 'traditional') {
    isTraditional.value = true
    setScriptAttr(true)
    // 等页面内容渲染完成后再转换，避免转换早于内容挂载
    setTimeout(() => applyConversion(true), 50)
  }
})
</script>

<template>
  <button class="script-toggle" @click="toggle" :aria-pressed="isTraditional">
    {{ isTraditional ? '简体' : '繁體' }}
  </button>
</template>

<style scoped>
.script-toggle {
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 13px;
  background: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  cursor: pointer;
  margin-left: 8px;
}
.script-toggle:hover {
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
}
</style>
