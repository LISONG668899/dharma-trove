import { defineConfig } from 'vitepress'

export default defineConfig({
  title: '藏汉佛教精华',
  description: 'DharmaTrove — 藏汉佛教典籍精华',
  lang: 'zh-CN',

  // <head> 标签注入：浏览器标签图标、手机主屏图标、社交分享卡片
  // 静态图片文件放在 docs/public/ 下，构建时会被原样拷到网站根目录，
  // 所以这里引用路径直接从 / 开始，不用写 /public/
  head: [
    // 浏览器标签页图标（favicon）
    ['link', { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/favicon-16x16.png' }],
    ['link', { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32x32.png' }],
    ['link', { rel: 'icon', href: '/favicon.ico' }],

    // iOS「添加到主屏幕」图标
    ['link', { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' }],

    // Android / PWA 图标清单
    ['link', { rel: 'manifest', href: '/site.webmanifest' }],
    ['meta', { name: 'theme-color', content: '#c9982f' }],

    // 社交平台转发卡片（微信/微博/Twitter等分享时显示的横幅图）
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:title', content: '藏汉佛教精华 · DharmaTrove' }],
    ['meta', { property: 'og:description', content: '唯识、中观、华严、禅宗、净土、大手印、大圆满——藏汉佛教典籍精华白话转译' }],
    ['meta', { property: 'og:image', content: '/og-image.png' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:image', content: '/og-image.png' }]
  ],

  themeConfig: {
    // 导航栏左上角 Logo
    logo: '/logo.png',

    // 导航栏顺序：关于我们排最前，综合排最后，中间按内容体系排列
    nav: [
      { text: '首页', link: '/' },
      { text: '关于我们', link: '/about' },
      { text: '唯识', link: '/唯识/' },
      { text: '中观', link: '/中观/' },
      { text: '华严', link: '/华严/' },
      { text: '禅宗', link: '/禅宗/' },
      { text: '净土', link: '/净土/' },
      { text: '大手印', link: '/大手印/' },
      { text: '大圆满', link: '/大圆满/' },
      { text: '综合', link: '/综合/' }
    ],

    sidebar: {
      '/唯识/': [{ text: '唯识', link: '/唯识/' }],
      '/中观/': [{ text: '中观', link: '/中观/' }],
      '/华严/': [{ text: '华严', link: '/华严/' }],
      '/禅宗/': [{ text: '禅宗', link: '/禅宗/' }],
      '/净土/': [{ text: '净土', link: '/净土/' }],
      '/大手印/': [{ text: '大手印', link: '/大手印/' }],
      '/大圆满/': [{ text: '大圆满', link: '/大圆满/' }],
      '/综合/': [{ text: '综合', link: '/综合/' }]
    },

    footer: {
      message: '藏汉佛教精华 · DharmaTrove',
      copyright: 'Copyright © 2026'
    },

    outline: {
      label: '本页目录'
    }
  },

  srcExclude: ['**/README.md']
})
