# 藏汉佛教精华 · DharmaTrove

## 本地运行

```bash
npm install
npm run docs:dev
```

浏览器打开命令行提示的地址（通常是 http://localhost:5173）即可预览。

## 新增文章

1. 在对应类目文件夹下新建一个 `.md` 文件，例如 `docs/dashouyin/降雷大手印导论.md`
2. 文件开头写 frontmatter：

```yaml
---
title: 降雷大手印导论
date: 2026-08-26
author: 译者姓名
---
```

3. 正文用简体中文撰写，Markdown 格式
4. 打开对应类目的 `index.md`（如 `docs/dashouyin/index.md`），在文章列表里加一行链接：

```html
<li><a href="/dashouyin/降雷大手印导论">降雷大手印导论</a><span class="dt-article-date">2026-08-26</span></li>
```

## 部署到 Cloudflare Pages

构建命令：`npm run docs:build`
构建输出目录：`docs/.vitepress/dist`

推送到 GitHub 后，在 Cloudflare Pages 里新建项目并连接该仓库，按上面两项填写即可自动部署。
