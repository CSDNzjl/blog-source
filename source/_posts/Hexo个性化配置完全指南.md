---
title: Hexo 个性化配置完全指南
date: 2026-05-29 14:00:00
updated: 2026-05-29 18:00:00
categories: [Hexo, 配置]
tags: [Hexo, Butterfly, 主题, 插件, 配置]
---

本文汇总 Hexo 博客除「写 Markdown 文章」之外的可定制项，并说明本仓库当前的实际配置，便于后续扩展。

---

## 1. 站点基础信息（`_config.yml`）

根目录 `_config.yml` 控制全站行为，建议优先配置：

| 配置项 | 作用 | 本仓库当前值 |
|--------|------|-------------|
| `title` | 站点标题 | CSDNzjl 的技术笔记 |
| `subtitle` | 副标题 | 服务器 · 部署 · 开发 |
| `description` | SEO 描述 | 记录服务器部署、Hexo 博客搭建与开发实践 |
| `author` | 作者名 | CSDNzjl |
| `language` | 语言 | zh-CN |
| `timezone` | 时区 | Asia/Shanghai |
| `url` | 站点地址（**必须正确**） | https://CSDNzjl.github.io |

```yaml
title: CSDNzjl 的技术笔记
subtitle: '服务器 · 部署 · 开发'
description: '记录服务器部署、Hexo 博客搭建与开发实践'
keywords: Hexo, 部署, GitHub Pages, Nginx, Spring Cloud, Butterfly
language: zh-CN
timezone: 'Asia/Shanghai'
url: https://CSDNzjl.github.io
```

> `url` 填错会导致 RSS、sitemap、绝对链接全部指向错误域名。

---

## 2. 文章与 URL 规则

### 2.1 单篇文章 Front Matter

每篇 `source/_posts/*.md` 顶部可写 YAML 元数据：

```yaml
---
title: 文章标题
date: 2026-05-29 12:00:00
updated: 2026-05-29 18:00:00
categories: [部署, Hexo]
tags: [GitHub Pages, 博客]
cover: /images/cover.jpg   # 封面图（Butterfly 主题支持）
top: true                  # 部分主题支持置顶
---
```

### 2.2 全局写作配置

```yaml
permalink: :year/:month/:day/:title/   # 文章 URL 格式
post_asset_folder: true                # 每篇文章独立资源目录
new_post_name: :title.md               # hexo new 生成的文件名
external_link:
  enable: true                         # 外链新窗口打开
```

**`post_asset_folder: true` 的用法：**

文章 `source/_posts/我的教程.md` 对应资源目录 `source/_posts/我的教程/`，图片放在其中，引用方式：

```markdown
![示意图](示意图.png)
```

### 2.3 分类与标签 URL 映射

中文分类可映射为英文路径，更利于 SEO：

```yaml
category_map:
  部署: deploy
  Hexo: hexo
  配置: config
tag_map:
  GitHub Pages: github-pages
  Spring Cloud: spring-cloud
```

---

## 3. 除文章外的页面与数据

`source/` 目录不仅放 `_posts/`：

| 路径 | 用途 | 创建命令 |
|------|------|----------|
| `source/about/index.md` | 关于页 | `hexo new page about` |
| `source/categories/index.md` | 分类总览（Butterfly 需要） | 手动创建，`type: categories` |
| `source/tags/index.md` | 标签总览（Butterfly 需要） | 手动创建，`type: tags` |
| `source/friends/index.md` | 友链页 | `hexo new page friends` |
| `source/_data/*.yml` | 全局数据（导航、友链列表等） | 手动创建 |
| `source/images/` | 静态图片，原样发布 | 手动放置 |

自定义页面示例：

```bash
hexo new page about
```

---

## 4. 主题配置（Butterfly）

本仓库已从默认 `landscape` 切换为 **[Butterfly](https://butterfly.js.org/)** 主题，外观更现代，支持卡片布局、侧边栏目录、代码块工具栏等。

### 4.1 安装与切换

```bash
pnpm add hexo-theme-butterfly hexo-renderer-pug moment-timezone
```

`_config.yml` 中设置：

```yaml
theme: butterfly
```

主题专属配置写在 **`_config.butterfly.yml`**（不要直接改 `node_modules` 里的主题文件）。

### 4.2 本仓库已配置项

| 配置 | 说明 |
|------|------|
| `nav.fixed` | 导航栏固定顶部 |
| `menu` | 首页 / 归档 / 分类 / 标签 / 关于 |
| `avatar.img` | 自定义头像 `/images/avatar.png` |
| `aside.card_*` | 已关闭分类/标签/归档/最新文章侧边栏 |
| `busuanzi` | 已关闭访客数与浏览量 |
| `search.use` | 本地搜索 `local_search` |
| `code_blocks.theme` | 代码高亮主题 `pale night` |
| `code_blocks.height_limit` | 超长代码块默认折叠（400px） |
| `cover.index_enable` | 首页卡片不显示封面图 |
| `pjax` / `lazyload` | 已开启页面切换与图片懒加载 |
| `toc.post` | 文章页右侧自动目录 |
| `post_copyright` | 文末版权声明 |
| `social` | GitHub 社交链接 |

### 4.3 代码高亮注意

使用 Butterfly 自带代码高亮时，需**关闭** Hexo 内置高亮，避免冲突：

```yaml
highlight:
  enable: false
prismjs:
  enable: false
```

代码块样式在 `_config.butterfly.yml` 的 `code_blocks` 中调整。

### 4.4 进一步美化

可在 `_config.butterfly.yml` 继续探索：

- `cover.default_cover`：文章默认封面图列表
- `default_top_img`：页面顶部横幅
- `subtitle`：首页打字机效果副标题
- `inject`：自定义 CSS / JS
- 评论系统（Gitalk、Twikoo、Waline 等）
- RSS 订阅（`hexo-generator-feed`）

官方文档：[https://butterfly.js.org/](https://butterfly.js.org/)

---

## 5. 插件

### 5.1 文章目录（Butterfly 侧边栏）

本仓库使用 **Butterfly 主题自带目录**，无需额外插件。在 `_config.butterfly.yml` 中：

```yaml
toc:
  post: true        # 文章页显示侧边栏目录
  number: true      # 显示章节编号
  scroll_percent: true

anchor:
  auto_update: true      # 滚动时 URL 同步锚点
  click_to_scroll: true  # 点击标题可跳转
```

标题锚点由 Hexo 内置的 `hexo-renderer-marked` 自动生成（`headerIds: true`），目录链接与标题 `id` 一一对应，点击即可跳转。

> **注意：** 不要与 `hexo-toc` 插件同时使用。该插件会把 `id` 放在标题内的 `<span>` 上，导致 Butterfly 目录链接缺少 `href`，出现「能看见但点不动」的问题。

某篇文章若不想出现在 sitemap 中，可在 Front Matter 加：

```yaml
sitemap: false
```

### 5.2 站点地图（hexo-generator-sitemap）

已安装 `hexo-generator-sitemap`，执行 `hexo generate` 后自动生成 `public/sitemap.xml`，便于搜索引擎收录。

`_config.yml` 配置：

```yaml
sitemap:
  path:
    - sitemap.xml
  rel: true    # 在页面 <head> 中插入 sitemap 链接
```

部署后访问：`https://CSDNzjl.github.io/sitemap.xml`

部署后访问：`https://CSDNzjl.github.io/sitemap.xml`

### 5.3 本地搜索（hexo-generator-searchdb）

已安装 `hexo-generator-searchdb`，配合 Butterfly 本地搜索使用。

`_config.yml` 生成搜索数据：

```yaml
search:
  path: search.json
  field: post
  content: true
  format: striptags
```

`_config.butterfly.yml` 启用搜索：

```yaml
search:
  use: local_search
  placeholder: 搜索文章...
  local_search:
    preload: true
```

导航栏会出现搜索图标，点击即可全文检索文章。

### 5.4 其他常用插件（可按需安装）

| 插件 | 功能 |
|------|------|
| `hexo-generator-feed` | RSS 订阅 |
| `hexo-wordcount` | 字数与阅读时长 |
| `hexo-baidu-url-submit` | 百度收录推送 |
| `hexo-generator-searchdb` | 本地全文搜索数据 |

安装示例：

```bash
pnpm add hexo-generator-feed
```

---

## 6. 脚手架模板（`scaffolds/`）

`hexo new "标题"` 生成的文章结构由 `scaffolds/post.md` 决定。本仓库模板：

```markdown
---
title: {{ title }}
date: {{ date }}
updated: {{ date }}
categories:
tags:
---
```

可按个人习惯预置默认分类、版权声明等。

另有 `scaffolds/page.md`（页面）、`scaffolds/draft.md`（草稿）。

---

## 7. 分页与首页

```yaml
index_generator:
  per_page: 10      # 首页每页文章数
  order_by: -date   # 按日期倒序

per_page: 10        # 归档/分类/标签页分页
date_format: YYYY-MM-DD
time_format: HH:mm:ss
```

Butterfly 首页卡片布局在 `_config.butterfly.yml` 的 `index_layout` 中调整（1–7 种样式）。

---

## 8. 部署配置

本仓库使用 Git 部署到 GitHub Pages：

```yaml
deploy:
  type: git
  repository: git@github.com:CSDNzjl/CSDNzjl.github.io.git
  branch: main
```

依赖插件：`hexo-deployer-git`

**双仓库工作流：**

| 仓库 | 内容 | 命令 |
|------|------|------|
| `blog-source` | Markdown 源码、配置 | `git push` |
| `CSDNzjl.github.io` | 编译后的静态网站 | `hexo deploy` |

建议顺序：**先 push 源码，再 deploy 网站**。

---

## 9. 源码仓库应忽略的文件（`.gitignore`）

```gitignore
node_modules/
public/          # hexo generate 生成物
.deploy_git/     # hexo deploy 临时目录
db.json          # Hexo 缓存
.DS_Store
Thumbs.db
```

---

## 10. 日常发布流程

```bash
# 1. 写新文章
hexo new "我的文章标题"

# 2. 本地预览
pnpm preview
# 或 hexo server → http://localhost:4000

# 3. 生成静态文件
pnpm build

# 4. 备份源码
git add .
git commit -m "post: 新文章"
git push

# 5. 发布网站
pnpm deploy
```

---

## 11. 配置文件速查

| 文件 | 作用 |
|------|------|
| `_config.yml` | Hexo 主配置（站点信息、插件、部署） |
| `_config.butterfly.yml` | Butterfly 主题配置 |
| `source/_posts/*.md` | 博客文章 |
| `source/about/index.md` | 关于页 |
| `source/categories/index.md` | 分类总览页 |
| `source/tags/index.md` | 标签总览页 |
| `scaffolds/post.md` | 新建文章模板 |
| `source/images/` | 静态图片 |
| `package.json` | 依赖与 npm 脚本（`build` / `preview` / `deploy`） |

---

## 12. 本仓库已安装依赖一览

```json
{
  "hexo-theme-butterfly": "主题",
  "hexo-deployer-git": "Git 部署",
  "hexo-generator-sitemap": "站点地图",
  "hexo-generator-searchdb": "本地搜索数据",
  "hexo-renderer-pug": "Butterfly 依赖",
  "moment-timezone": "Butterfly 依赖"
}
```

---

## 参考链接

- [Hexo 官方文档](https://hexo.io/zh-cn/docs/)
- [Butterfly 主题文档](https://butterfly.js.org/)
- [Hexo 插件列表](https://hexo.io/plugins/)
- [hexo-generator-sitemap](https://github.com/hexojs/hexo-generator-sitemap)
