# 藏汉佛教精华 · DharmaTrove

## 本地运行

```bash
npm install
npm run docs:dev
```

浏览器打开命令行提示的地址（通常是 http://localhost:5173）即可预览。

## 新增文章

1. 在对应类目文件夹下新建一个 `.md` 文件，例如 `docs/大手印/降雷大手印导论.md`
2. 文件开头写 frontmatter：

```yaml
---
title: 降雷大手印导论
date: 2026-08-26
author: 译者姓名
---
```

3. 正文用简体中文撰写，Markdown 格式
4. 打开对应类目的 `index.md`（如 `docs/大手印/index.md`），在文章列表里加一行链接：

```html
<li><a href="/大手印/降雷大手印导论">降雷大手印导论</a><span class="dt-article-date">2026-08-26</span></li>
```

## 类目文件夹对照

| 文件夹（中文） | 对应内容 |
| --- | --- |
| 唯识 | 唯识类文章 |
| 中观 | 中观类文章 |
| 华严 | 华严类文章 |
| 禅宗 | 禅宗类文章 |
| 密宗 | 密宗类文章 |
| 大手印 | 大手印类文章 |
| 大圆满 | 大圆满类文章 |
| 随笔 | 闻思心得随笔 |

## 部署到 Cloudflare Pages

构建命令：`npm run docs:build`
构建输出目录：`docs/.vitepress/dist`

推送到 GitHub 后，在 Cloudflare Pages 里新建项目并连接该仓库，按上面两项填写即可自动部署。

## Cloudflare Pages 古籍数据迁移至 R2

`docs/public/canon/` 保留在 GitHub，供本地开发、数据生成和备份使用。构建时可将其部署副本同步到 R2；网页以及全文搜索继续使用 `/canon/` 路径，选段翻译也从当前部署对应的原典版本读取。

Cloudflare 后台配置（只需一次）：

1. 创建 Standard R2 bucket，例如 `dharma-trove-canon`，保持私有。
2. 在 R2 创建仅适用于此 bucket 的 Object Read & Write API token。将 S3 访问密钥保存到 Pages 项目的**构建环境**变量中。
3. 在 Pages 项目 Settings → Bindings 添加 R2 bucket，变量名为 `CANON_R2`。生产与预览环境都使用 R2 时，两处均需配置绑定。
4. 在构建环境设置以下变量，密钥标记为机密，并启用迁移：

   | 变量 | 值 |
   | --- | --- |
   | `CANON_R2_ENABLED` | `1` |
   | `CANON_R2_ACCOUNT_ID` | Cloudflare 账户 ID |
   | `CANON_R2_BUCKET` | 实际 R2 bucket 名称 |
   | `CANON_R2_ACCESS_KEY_ID` | R2 S3 Access Key ID |
   | `CANON_R2_SECRET_ACCESS_KEY` | R2 S3 Secret Access Key |

5. 保持构建命令 `npm run docs:build`，构建输出 `docs/.vitepress/dist`，重新部署。日志出现 `Canon R2 verified ... files` 表示同步和文件数量校验成功。

每份数据快照以内容摘要命名，新的部署仅在完整上传并校验后才移除构建产物中的 `canon/` 副本。经文内容未变时后续构建只需列目录校验，不用再次上传。旧快照保留供上一版及回滚读取，不要直接清理仍在使用的快照。关闭 `CANON_R2_ENABLED` 后构建保留本地静态文件（仍受 Pages 文件数量限制）。
