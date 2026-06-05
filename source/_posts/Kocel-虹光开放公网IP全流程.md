---
title: 虹光项目：开放公网 IP 访问全流程
date: 2026-06-05 10:00:00
updated: 2026-06-05 16:00:00
categories:
  - Kocel
tags:
  - Kocel
  - 虹光
  - Nginx
  - 公网
  - CORS
  - 部署
cover: /images/hongguang-logo.png
---

本文记录在 **hongguang（虹光铸造全生命周期管理系统）** 测试环境中，将内网服务通过公网 IP 对外开放的完整流程，包括 License 配置、Nginx 反向代理、前端打包改造，以及公网访问时常见的跨域 / 私有网络拦截问题排查。

> **适用读者**：实施、运维、全栈开发。  
> **前置知识**：了解项目基本架构（Nginx + Gateway + Nacos + 微服务），可参考 [虹光项目：服务器部署架构与从零搭建指南](/2026/05/29/虹光项目：服务器部署架构与从零搭建指南/)。

---

## 1. 环境背景

### 1.1 局域网（测试服务器）

| 组件 | 地址 | 说明 |
|------|------|------|
| 前端 Nginx | `192.168.2.206:80` | 静态资源 `dist/`，内网用户日常访问 |
| 公网映射 Nginx | `192.168.2.206:8001` | 与 80 端口逻辑相同，供公网入口转发 |
| API 网关 | `192.168.2.206:3000` | Spring Cloud Gateway，仅内网可达 |

### 1.2 公网入口

| 项目 | 值 |
|------|-----|
| 公网 IP | `221.193.232.137:8001` |
| 转发规则 | 公网 `:8001` → 局域网 `192.168.2.206:8001` |

公网映射只负责把流量送到 Nginx 8001 端口，**不会**自动把 API 请求代理到网关 3000——后者需要 Nginx 配置 + 前端打包配合完成。

---

## 2. License 配置

auth-server 启动前需加载 License 证书，配置位于 `bootstrap.yaml`：

```yaml
springboot:
  license:
    verify:
      subject: kocel
      publicAlias: publiccert
      publicKeysStorePath: /publicCerts.store
      storePass: kocel123456
      licensePath: /home/license/license.lic
```

**操作步骤：**

1. 获取 `license.lic` 文件；
2. 放到服务器 `/home/license/license.lic`；
3. 重启 **auth-server** 服务，使证书生效。

---

## 3. 内网访问时的请求链路

内网用户通过 `192.168.2.206:80` 访问时，前端在打包时写死了网关地址（`.env.production`）：

```properties
VUE_APP_BASE_API = 'http://192.168.2.206:3000'
```

**完整请求示例：**

```text
浏览器
  → GET http://192.168.2.206:3000/hongguang-parameter/BaseTableSelfDefinedHead/getByParams?n=...
网关 (:3000)
  → 按路径前缀 /hongguang-parameter/ 匹配路由
  → 从 Nacos 发现 hongguang-parameter 实例
  → 转发到对应微服务处理并返回
```

**数据流转：**

```text
局域网用户 ⇄ Nginx :80（静态页面）⇄ Gateway :3000 ⇄ 具体微服务
```

> **要点**：前端不会在运行时查 Nacos；`VUE_APP_BASE_API` 在 `npm run build:prod` 时编译进 JS，改配置后必须重新打包并上传 `dist`。

### 3.2 为什么内网 80 + 3000 没有 CORS 问题？

常见疑问：前端走 Nginx **80** 端口，API 直连网关 **3000** 端口，端口不同，为什么没有 CORS 报错？

#### 端口不同，确实不是「同源」

浏览器同源策略要求 **协议 + 域名 + 端口** 三者完全相同：

| 页面 | API | 是否同源 |
|------|-----|----------|
| `http://192.168.2.206:80` | `http://192.168.2.206:3000` | ❌ 不同源（端口不同） |

内网场景并不是「没有跨域」，而是 **跨域被网关 CORS 配置兜住**，且 **没有触发私有网络访问（PNA）限制**。

#### 原因一：网关已返回 CORS 响应头

`hongguang-gateway` 中有全局 CORS 配置（`GlobalGatewayCorsConfig`），允许任意来源、任意方法、任意请求头：

```java
configuration.setAllowCredentials(true);
configuration.addAllowedOrigin(CorsConfiguration.ALL);  // 允许 *
configuration.addAllowedHeader(CorsConfiguration.ALL);
configuration.addAllowedMethod(CorsConfiguration.ALL);
```

浏览器从 `:80` 页面请求 `:3000` 时，网关会在响应中带上 `Access-Control-Allow-Origin` 等头，浏览器校验通过后放行。前端 `request.js` 中 `withCredentials: false`，与网关返回 `*` 也兼容。

#### 原因二：同属私网，不触发 PNA 限制

公网报错中的 `more-private address space local` 来自 Chrome 的 **Private Network Access（私有网络访问）** 策略：

| 场景 | 页面来源 | API 目标 | 浏览器行为 |
|------|----------|----------|------------|
| 内网 | `192.168.2.206:80`（私网） | `192.168.2.206:3000`（私网） | 同属 local 私网空间，**不拦截** |
| 公网 | `221.193.232.137:8001`（公网） | `192.168.2.206:3000`（私网） | 公网 → 私网，**直接拦截** |

内网是「私网页面访问私网 API」；公网是「公网页面访问内网 IP」——这是比 CORS 更底层的限制，**在 Nginx 上加 CORS 头也无法绕过**。

#### 原因三：内网用户网络可达

内网用户与 `192.168.2.206` 在同一局域网，浏览器可以直接连 `:3000`。公网用户无法路由到 `192.168.x.x`，即便没有 CORS 限制也会请求失败。

#### 内网 vs 公网对比

```text
内网（80 页面 + 3000 API 直连）：
  页面 :80 ──跨端口，但同私网──> API :3000
              ↑
        网关 CORS 放行 + 无 PNA 限制 + 网络可达  →  正常使用 ✅

公网（8001 页面 + 3000 API 直连）：
  页面 公网:8001 ──跨网段──> API 192.168.x.x:3000
              ↑
        PNA 直接拦截（CORS 配置无效）  →  登录失败 ❌
```

因此公网改造必须让 API 也走 Nginx 同源代理（`/api`），详见下一节。

---

## 4. 公网访问的核心改造

### 4.1 为什么不能直接沿用内网配置

若公网用户访问 `http://221.193.232.137:8001`，而 `dist` 中 API 仍指向 `http://192.168.2.206:3000`，会出现两类问题：

| 问题 | 表现 | 原因 |
|------|------|------|
| 私有网络访问拦截 | `blocked by CORS policy: ... more-private address space local` | Chrome 禁止公网页面直接请求 `192.168.x.x` 私网地址 |
| 网络不可达 | 请求超时 / Failed to fetch | 公网用户无法路由到内网 IP |

在 Nginx 8001 上添加 `Access-Control-Allow-Origin` **无法解决**上述问题——因为 API 请求根本没有经过 Nginx，而是浏览器直连内网 3000 端口。

### 4.2 正确思路：API 与页面对同源

让浏览器只访问公网入口，由 Nginx 在服务端转发到本机网关：

```text
浏览器（公网）
  → http://221.193.232.137:8001/api/hongguang-xxx/...
Nginx :8001（192.168.2.206）
  → http://127.0.0.1:3000/hongguang-xxx/...   （服务端内部转发，浏览器不参与）
Gateway :3000
  → Nacos 路由到具体微服务
```

**公网数据流转：**

```text
用户 ⇄ 公网 :8001 ⇄ Nginx :8001 ⇄ Gateway :3000 ⇄ 具体微服务
         ↑ 页面与 /api 同源，浏览器放行
```

---

## 5. 改造步骤

### 5.1 修改前端打包配置

编辑 `hongguang-web/.env.production`：

```properties
# 改为相对路径，与页面同源，彻底避免跨域和私有网络拦截
VUE_APP_BASE_API = '/api'
```

**为什么用 `/api` 而不是写死公网地址？**

- 相对路径自动跟随当前访问域名（公网 IP、域名、端口均无需改代码）；
- Nginx 已有 `/api/` → `127.0.0.1:3000/` 的反向代理规则。

**不要用：**

```properties
# ❌ 公网页面 + 内网 API，浏览器会拦截
VUE_APP_BASE_API = 'http://192.168.2.206:3000'

# ❌ 换域名/IP 就要重新打包
VUE_APP_BASE_API = 'http://221.193.232.137:8001/api'
```

### 5.2 重新打包并部署

```bash
cd hongguang-web
npm run build:prod
```

将 `dist/` 目录全部文件上传到服务器 Nginx 的 `root` 路径（如 `/hongguang/deploy/web/dist`），覆盖旧文件。**无需重启 Java 服务**。

### 5.3 Nginx 增加 8001 端口配置

8001 端口配置可直接照搬 80 端口，核心是 `/api/` 反向代理：

```nginx
server {
    listen 8001 default_server;
    listen [::]:8001 default_server;
    server_name _;

    index index.html index.htm default.htm default.html;
    client_max_body_size 300m;
    root /hongguang/deploy/web/dist;

    client_header_buffer_size 128k;
    large_client_header_buffers 4 128k;

    location /flc-jimureport/ {
        proxy_pass http://127.0.0.1:8370/;
        proxy_set_header Cookie $http_cookie;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /jmreport/ {
        proxy_pass http://127.0.0.1:8370/jmreport/;
        proxy_set_header Cookie $http_cookie;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    # 关键：/api/ 前缀转发到本机网关，去掉 /api 后拼到 3000
    location /api/ {
        proxy_pass http://127.0.0.1:3000/;
        proxy_set_header Cookie $http_cookie;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /boot-admin/ {
        proxy_pass http://127.0.0.1:60097;
        proxy_set_header Cookie $http_cookie;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /websocket/ {
        proxy_pass http://127.0.0.1:9000/api/system/Message/websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 600s;
    }

    location /FileServer/ {
        proxy_pass http://192.168.201.40:8080/;
    }
}
```

> **说明**：同源访问时 **不需要** 在 Nginx 上配置 CORS 响应头。若后端网关也返回 CORS 头，nginx 再加一层反而可能出现重复头导致报错。

### 5.4 Nginx 常用运维命令

虹光测试服务器上，Nginx 配置文件通常在 `/etc/nginx/sites-enabled/default`（或 `sites-available/` 下对应文件）。修改配置的标准流程：**备份 → 编辑 → 测试 → 重载**。

#### 配置文件位置

```bash
# 查看主配置（会 include sites-enabled 等目录）
nginx -t

# 常见站点配置路径（Debian / Ubuntu）
/etc/nginx/sites-enabled/default
/etc/nginx/sites-available/default

# 虹光 dist 静态资源目录（与 server.root 一致）
/hongguang/deploy/web/dist
```

#### 修改前备份

```bash
sudo cp /etc/nginx/sites-enabled/default \
        /etc/nginx/sites-enabled/default.bak.$(date +%Y%m%d)
```

#### 编辑配置

```bash
# 任选其一
sudo vim /etc/nginx/sites-enabled/default
sudo nano /etc/nginx/sites-enabled/default
```

#### 测试并重载（改完必做）

```bash
# 1. 检查语法是否正确（有 error 则不要 reload）
sudo nginx -t

# 2. 语法通过后，平滑重载（不中断现有连接，推荐）
sudo nginx -s reload

# 合并为一行（日常最常用）
sudo nginx -t && sudo nginx -s reload
```

#### 服务启停与状态

```bash
# 查看运行状态
sudo systemctl status nginx

# 启动 / 停止 / 重启（reload 失败或首次安装时用）
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx

# 开机自启
sudo systemctl enable nginx
```

#### 查看端口与进程

```bash
# 确认 80 / 8001 是否在监听
sudo ss -tlnp | grep nginx
# 或
sudo netstat -tlnp | grep nginx

# 查看 nginx 主进程及 worker
ps aux | grep nginx
```

#### 查看日志（502 / 404 排查）

```bash
# 错误日志（配置语法、代理 upstream 失败等）
sudo tail -f /var/log/nginx/error.log

# 访问日志（请求是否到达 nginx）
sudo tail -f /var/log/nginx/access.log

# 只看最近 50 行错误
sudo tail -n 50 /var/log/nginx/error.log
```

#### 常用命令速查

| 场景 | 命令 |
|------|------|
| 改完配置，确认无误并生效 | `sudo nginx -t && sudo nginx -s reload` |
| 配置有语法错误 | `sudo nginx -t`，按报错行号回编辑器修改 |
| 页面 502，查代理是否通 | `sudo tail -f /var/log/nginx/error.log` |
| 确认 8001 已监听 | `ss -tlnp \| grep 8001` |
| 重载后仍异常，硬重启 | `sudo systemctl restart nginx` |

> **注意**：`nginx -s reload` 前务必先 `nginx -t` 通过；否则错误配置可能导致 reload 失败或 nginx 无法正常工作。若 `reload` 报错，用 `systemctl status nginx` 和 `error.log` 定位问题，必要时从 `.bak` 备份恢复。

---

## 6. 公网完整请求示例

以查询参数表头为例，改造后的请求路径：

```text
1. 浏览器发起：
   http://221.193.232.137:8001/api/hongguang-parameter/BaseTableSelfDefinedHead/getByParams?n=1780640478

2. 公网映射 → 192.168.2.206:8001

3. Nginx 匹配 location /api/，转发到：
   http://127.0.0.1:3000/hongguang-parameter/BaseTableSelfDefinedHead/getByParams?n=1780640478

4. Gateway 按 /hongguang-parameter/ 前缀路由到对应微服务
```

登录接口同理：

```text
http://221.193.232.137:8001/api/hongguang-auth-server/oauth/token
  → 127.0.0.1:3000/hongguang-auth-server/oauth/token
```

---

## 7. 验证与排查

### 7.1 如何确认改造生效

1. 浏览器打开 `http://221.193.232.137:8001`，F12 → **Network**；
2. 登录或刷新页面，检查 API 请求 URL：
   - ✅ 正确：`http://221.193.232.137:8001/api/hongguang-xxx/...`
   - ❌ 仍是旧包：`http://192.168.2.206:3000/hongguang-xxx/...`
3. 若仍是内网地址，说明 `dist` 未更新——检查是否执行了 `build:prod` 以及上传目录是否正确。

### 7.2 常见报错对照

| 报错关键词 | 含义 | 处理 |
|------------|------|------|
| `more-private address space local` | 公网页面向内网 IP 发请求，被浏览器私有网络策略拦截 | 改 `VUE_APP_BASE_API = '/api'` 并重新打包 |
| `Access-Control-Allow-Origin` | 跨域，页面与 API 不同源 | 同上，让 API 走 `/api` 同源代理 |
| 页面能开，登录 502 | Nginx 代理或网关未启动 | 检查 3000 端口 gateway 进程、nginx 错误日志 |
| 401 Unauthorized | Token / 账号问题 | 与公网改造无关，单独排查 auth 服务 |

### 7.3 其他注意项

1. **文件上传路径**：`define.js` 中 `comUploadUrl` 为 `VUE_APP_BASE_API + '/api/file/Uploader'`，改为 `/api` 后实际路径为 `/api/api/file/Uploader`，若上传异常需单独检查；
2. **WebSocket**：若消息推送异常，需确认 `VUE_APP_BASE_WSS` 是否指向 `ws://公网IP:8001/websocket/` 等 nginx 代理路径；
3. **License**：公网访问不影响 License 校验，但 auth-server 必须能读到 `/home/license/license.lic`。

---

## 8. 内网 vs 公网对比

| 对比项 | 内网访问 (:80) | 公网访问 (:8001) |
|--------|----------------|------------------|
| 页面入口 | `192.168.2.206:80` | `221.193.232.137:8001` |
| `VUE_APP_BASE_API` | 可写 `http://192.168.2.206:3000` | 必须写 `/api` |
| API 实际路径 | 直连网关 3000 | 经 Nginx `/api/` 代理到 3000 |
| 是否需要 CORS | 否（或网关统一处理） | 否（同源，无需额外 CORS） |
| 打包要求 | 改 IP 后需 rebuild | 改 `/api` 后需 rebuild |

---

## 9. 小结

开放公网 IP 访问的关键不是给 Nginx 堆 CORS 头，而是：

1. **License** 放到 `/home/license/` 并重启 auth-server；
2. **Nginx 8001** 增加与 80 端口一致的配置，确保 `/api/` 代理到 `127.0.0.1:3000`；改完后执行 `sudo nginx -t && sudo nginx -s reload`；
3. **前端** 将 `VUE_APP_BASE_API` 改为 `/api`，重新 `build:prod` 并上传 `dist`；
4. **验证** Network 面板中 API 请求已走 `公网IP:8001/api/...`，而非内网 `192.168.x.x:3000`。

按以上步骤完成后，公网用户即可正常登录和使用系统。
