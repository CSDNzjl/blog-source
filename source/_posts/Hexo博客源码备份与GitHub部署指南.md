---
title: Hexo 博客源码备份与 GitHub Pages 部署指南
---

本文整理自 [Hexo + GitHub Pages 搭建个人博客](https://zhuanlan.zhihu.com/p/392994381) 类教程的常见流程，并补充**源码备份**说明。很多教程只教 `hexo deploy`，容易让人误以为 GitHub 上已有完整项目——实际上往往只有编译后的静态网站。

---

## 1. 先搞清楚：GitHub 上到底有什么

Hexo 博客在本地的典型目录结构：

```
blog/                    ← 博客源码（应单独备份）
├── source/
│   └── _posts/          ← 你写的 Markdown 文章
├── _config.yml          ← 博客配置
├── themes/              ← 主题（若自定义）
├── package.json
├── node_modules/        ← 依赖，不要提交
├── public/              ← hexo generate 生成的静态文件
└── .deploy_git/         ← hexo deploy 使用的临时 Git 目录
```

执行 `hexo deploy` 时，Hexo 会把 `public/` 里的内容推送到 `username.github.io` 仓库，供 GitHub Pages 展示。

| 内容 | 本地 | `username.github.io` 仓库 |
|------|------|---------------------------|
| `source/_posts/*.md` 文章原文 | ✅ | ❌ |
| `_config.yml` 配置 | ✅ | ❌ |
| `package.json`、主题源码 | ✅ | ❌ |
| 编译后的 `index.html`、CSS、JS | ✅（在 public/） | ✅ |

**结论：** `hexo deploy` 部署的是**成品网站**，不是**写作源码**。若只把 deploy 仓库当作备份，换电脑后无法直接继续用 Markdown 写博客。

---

## 2. 推荐方案：两个仓库分工

| 仓库 | 用途 | 更新方式 |
|------|------|----------|
| `CSDNzjl.github.io` | 存放编译后的静态网站，供 GitHub Pages 访问 | `hexo deploy` |
| `blog-source`（名称自定） | 存放 Hexo 源码，便于换机、协作、回滚 | `git push` |

两个仓库互不替代：一个给人看，一个给自己改。

---

## 3. 部署仓库配置（教程原有部分）

在博客根目录 `_config.yml` 末尾配置：

```yaml
deploy:
  type: git
  repository: git@github.com:你的用户名/你的用户名.github.io.git
  branch: main
```

安装部署插件：

```bash
pnpm add hexo-deployer-git
# 或 npm install hexo-deployer-git --save
```

常用命令：

```bash
hexo clean          # 清除缓存
hexo generate       # 生成静态文件到 public/
hexo deploy         # 推送到 github.io 仓库
# 可合并为：
hexo clean && hexo g -d
```

本地预览：

```bash
hexo server
# 浏览器访问 http://localhost:4000
```

---

## 4. 源码仓库：从零初始化

在 Hexo 项目根目录（与 `_config.yml` 同级）操作。

### 4.1 创建 .gitignore

以下内容**不要**提交到源码仓库：

```
node_modules/
public/
.deploy_git/
db.json
.DS_Store
```

说明：

- `node_modules/`：体积大，换机后 `pnpm install` 即可恢复
- `public/`、`db.json`：每次 `hexo generate` 会重新生成
- `.deploy_git/`：`hexo deploy` 内部使用的临时目录

### 4.2 初始化并推送到 GitHub

先在 GitHub 新建一个**空仓库**（例如 `blog-source`），再执行：

```bash
git init
git add .
git commit -m "init: hexo blog source"
git branch -M main
git remote add origin git@github.com:你的用户名/blog-source.git
git push -u origin main
```

之后每次改完文章或配置：

```bash
git add .
git commit -m "update: 新文章或配置说明"
git push
```

---

## 5. 日常写作与发布流程

```
1. 写/改文章     hexo new "标题"  或直接编辑 source/_posts/*.md
2. 本地预览     hexo server
3. 备份源码     git add . && git commit && git push   → blog-source
4. 发布网站     hexo clean && hexo g -d               → username.github.io
```

建议养成习惯：**先 push 源码，再 deploy 网站**。这样 GitHub 上始终有最新文章原文。

---

## 6. 换电脑后如何恢复

```bash
# 1. 克隆源码仓库（不是 github.io）
git clone git@github.com:你的用户名/blog-source.git
cd blog-source

# 2. 安装依赖
pnpm install
# 或 npm install

# 3. 本地预览，确认文章都在
hexo server

# 4. 配置 SSH 密钥后，继续部署网站
hexo deploy
```

若 `hexo deploy` 报错，检查：

- `_config.yml` 中 `deploy.repository` 是否指向正确的 `username.github.io`
- 本机是否已配置 GitHub SSH 密钥（`ssh -T git@github.com` 测试）

---

## 7. 常见问题

### Q1：`hexo deploy` 时 Git 只显示少量文件变更，是不是丢内容了？

不是。Git 只提交**有变化**的文件，仓库里仍是完整网站。这是正常现象。

### Q2：GitHub 上为什么看不到 `.md` 文件？

因为 deploy 仓库里只有 HTML。要看 Markdown 原文，请打开**源码仓库**（如 `blog-source`）。

### Q3：能否只用一个仓库？

可以，但不推荐新手使用。常见做法是：

- `main` 分支：放源码
- `gh-pages` 分支：放编译结果

需要额外改 deploy 配置，且与「用户名.github.io」默认用 `main` 展示页面的习惯容易混淆。两个仓库更清晰。

### Q4：文章里的图片怎么管理？

开启 `post_asset_folder: true` 后，每篇文章可有独立资源目录。图片应放在 `source/` 下，随源码仓库一起 `git push`；`hexo generate` 会一并打包进 `public/` 并由 deploy 推上 Pages。

---

## 8. 检查清单

换电脑前确认：

- [ ] 源码仓库已 push 最新 `source/_posts/` 文章
- [ ] `_config.yml`、主题自定义已提交
- [ ] 文章引用的本地图片已在 `source/` 中并提交
- [ ] 知道 `username.github.io` 与 `blog-source` 各自用途

---

## 9. 参考链接

- [Hexo 官方文档 - 部署](https://hexo.io/docs/one-command-deployment.html)
- [Hexo 官方文档 - 写作](https://hexo.io/docs/writing.html)
- [知乎：Hexo + GitHub Pages 搭建教程](https://zhuanlan.zhihu.com/p/392994381)
