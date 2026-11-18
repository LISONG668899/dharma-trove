import { h } from 'vue'
import DefaultTheme from 'vitepress/theme'
import ConvertToggle from './components/ConvertToggle.vue'
import SelectSave from './components/SelectSave.vue'
import SavedList from './components/SavedList.vue'
import SavedNavButton from './components/SavedNavButton.vue'
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
      'layout-bottom': () => h(SelectSave)
    })
  },
  enhanceApp({ app }) {
    app.component('ConvertToggle', ConvertToggle)
    app.component('SavedList', SavedList)
  }
} satisfies Theme
