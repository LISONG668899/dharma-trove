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
    ['meta', { property: 'og:description', content: '唯识中观、禅宗宝箧、密宗精华、大手印、大圆满——藏汉佛教典籍精华白话转译' }],
    ['meta', { property: 'og:image', content: '/og-image.png' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:image', content: '/og-image.png' }]
  ],

  themeConfig: {
    // 导航栏左上角 Logo
    logo: '/logo.png',

    nav: [
      { text: '首页', link: '/' },
      { text: '关于我们', link: '/about' },
      { text: '唯识', link: '/weishi/' },
      { text: '中观', link: '/zhongguan/' },
      { text: '华严', link: '/huayan/' },
      { text: '禅宗宝箧', link: '/chanzong-baoqie/' },
      { text: '密宗精华', link: '/mixu-jinghua/' },
      { text: '大手印', link: '/dashouyin/' },
      { text: '大圆满', link: '/dayuanman/' },
      { text: '闻思心得', link: '/wensi-xinde/' }
    ],

    sidebar: {
      '/weishi/': [{ text: '唯识', link: '/weishi/' }],
      '/zhongguan/': [{ text: '中观', link: '/zhongguan/' }],
      '/huayan/': [{ text: '华严', link: '/huayan/' }],
      '/chanzong-baoqie/': [{ text: '禅宗宝箧', link: '/chanzong-baoqie/' }],
      '/mixu-jinghua/': [{ text: '密宗精华', link: '/mixu-jinghua/' }],
      '/dashouyin/': [{ text: '大手印', link: '/dashouyin/' }],
      '/dayuanman/': [{ text: '大圆满', link: '/dayuanman/' }],
      '/wensi-xinde/': [{ text: '闻思心得', link: '/wensi-xinde/' }]
    },

    footer: {
      message: '藏汉佛教精华 · DharmaTrove',
      copyright: 'Copyright © 2026'
    },

    outline: {
      label: '本页目录'
    }
  },

  // 五个类目对应的静态路由，方便后续每个类目下新增文章时
  // VitePress 自动纳入构建（无需手动改这里）
  srcExclude: ['**/README.md']
})
