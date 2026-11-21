import { h, onMounted, watch } from 'vue'
import { useData } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import ConvertToggle from './components/ConvertToggle.vue'
import SelectSave from './components/SelectSave.vue'
import SavedList from './components/SavedList.vue'
import SavedNavButton from './components/SavedNavButton.vue'
import CanonButtons from './components/CanonButtons.vue'
import CanonReader from './components/CanonReader.vue'
import './custom.css'
import './tools.css'
import type { Theme } from 'vitepress'

export default {
  extends: DefaultTheme,
  Layout: () => {
    // nav-bar-content-after：导航栏右侧，放“收藏”按钮和简繁切换按钮
    // layout-bottom：划线收藏（选中文字后出现的按钮、已收藏段落的金色下划线），只在单篇文章里起作用
    // 页脚 Logo 用 custom.css 里的 ::before 方案，不需要在这里注入
    return h(DefaultTheme.Layout, null, {
      'nav-bar-content-after': () => [h(SavedNavButton), h(ConvertToggle)],
      'layout-bottom': () => h(SelectSave),
      // home-features-after：首页类目卡片下方，德格版《甘珠尔》《丹珠尔》两个按钮
      'home-features-after': () => h(CanonButtons)
    })
  },
  setup() {
    // 手机浏览器顶栏颜色跟着色调走：浅色金色，深色深蓝（与导航栏一致）
    const { isDark } = useData()
    onMounted(() => {
      watch(isDark, (d) => {
        document.querySelectorAll('meta[name="theme-color"]').forEach((m) => m.setAttribute('content', d ? '#142c43' : '#c9982f'))
      }, { immediate: true })
    })
  },
  enhanceApp({ app }) {
    app.component('ConvertToggle', ConvertToggle)
    app.component('SavedList', SavedList)
    app.component('CanonReader', CanonReader)
  }
} satisfies Theme
