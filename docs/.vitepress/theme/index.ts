import { h } from 'vue'
import DefaultTheme from 'vitepress/theme'
import ConvertToggle from './components/ConvertToggle.vue'
import './custom.css'
import type { Theme } from 'vitepress'

export default {
  extends: DefaultTheme,
  Layout: () => {
    // nav-bar-content-after 是导航栏右侧插槽，放简繁切换按钮
    // 页脚 Logo 改用 custom.css 里的 ::before 方案直接插在页脚文字上方，
    // 不再需要在这里注入组件
    return h(DefaultTheme.Layout, null, {
      'nav-bar-content-after': () => h(ConvertToggle)
    })
  },
  enhanceApp({ app }) {
    app.component('ConvertToggle', ConvertToggle)
  }
} satisfies Theme
