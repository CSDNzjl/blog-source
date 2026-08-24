---
title: 虹光项目：使用 ngrok 进行本地联调与快速验证
date: 2026-06-01 10:00:00
updated: 2026-06-01 10:00:00
categories:
  - Kocel
tags:
  - Kocel
  - ngrok
  - 虹光
  - 联调
  - Nacos
  - 调试
cover: /images/hongguang-logo.png
---

本文说明在 **hongguang（虹光铸造全生命周期管理系统）** 日常开发中，如何使用 [ngrok](https://ngrok.com/) 将本地服务暴露到公网，实现 **前端改动快速验证** 与 **后端断点联调** 两类场景。

> **适用读者**：前端 / 后端开发、实施与测试同事。  
> **前置知识**：了解项目基本架构（网关 + Nacos + 微服务），可参考 [虹光项目：服务器部署架构与从零搭建指南](/2026/05/29/虹光项目：服务器部署架构与从零搭建指南/)。

---

## 1. 为什么需要 ngrok

在虹光项目中，浏览器访问的是服务器上的前端（Nginx :93），API 请求经网关（:3000）转发到各微服务。本地开发时常见两类痛点：

| 场景 | 痛点 | ngrok 的作用 |
|------|------|--------------|
| **小改动快速验证** | 本地改完前端需 `build` 再上传 `dist`，耗时长 | 本地启动前端 dev server，用 ngrok 映射公网 URL，测试人员直接访问 |
| **后端断点调试** | Knife4j 手动填参、查库麻烦；本地服务注册到 Nacos 后，服务器网关无法访问内网 IP | ngrok 提供公网 HTTPS 入口，请求经隧道转发到本地 JAR，可配合 IDE 断点 |

**原理简述：**

```
测试人员浏览器 / 服务器网关
        │
        │  HTTPS（公网）
        ▼
  ngrok 公网域名（如 xxx.ngrok-free.dev:443）
        │
        │  隧道转发
        ▼
  本机 localhost:端口（前端 dev server 或后端微服务）
```

全程走 HTTPS，适合临时联调；**不适合作为生产环境方案**。

---

## 2. 环境准备

### 2.1 注册与安装 ngrok

1. 打开 [https://ngrok.com/](https://ngrok.com/) 注册账号（免费版即可）。
2. 在 Dashboard 获取 **Authtoken**，并在本机执行一次绑定：

```bash
ngrok config add-authtoken <你的 Authtoken>
```

3. 安装 ngrok CLI（任选一种方式）：

```bash
# Windows（Chocolatey）
choco install ngrok

# 或从官网下载 exe，加入 PATH
```

4. 验证安装：

```bash
ngrok version
```

---

## 3. 场景一：前端小改动 — 快速给测试验证

### 3.1 适用情况

- 样式、文案、简单交互等 **小改动**，希望测试当天就能验，不必等下班统一打包部署。
- 开发机已拉取最新代码，能正常 `npm run dev`。

### 3.2 操作步骤

**① 本地启动前端**

在 `hongguang-web` 目录：

```bash
npm install          # 首次
npm run dev          # 默认端口以 vue.config.js / .env.development 为准，常见为 8080 或 3000
```

确认浏览器能打开 `http://localhost:<端口>`。

**② 启动 ngrok 映射本地端口**

假设前端 dev server 在 **80** 端口（按实际端口替换）：

```bash
ngrok http 80
```

终端输出类似：

```text
Session Status                online
Account                       <your-account> (Plan: Free)
Version                       3.39.5
Region                        Asia Pacific (ap)
Latency                       133ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://<your-subdomain>.ngrok-free.dev -> http://localhost:80

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**③ 将公网地址发给测试 / 实施**

测试人员浏览器访问：

```text
https://<your-subdomain>.ngrok-free.dev
```

即可看到 **你本机正在运行的最新前端**，无需服务器上的旧 `dist`。

### 3.3 注意事项

1. **API 仍指向打包配置中的网关地址**（如 `http://192.168.1.200:3000`），本地前端只是「页面壳子」更新；若改动涉及新接口路径，需保证网关与后端已部署对应版本。
2. 开发机需 **能访问内网网关**（VPN 或同一局域网），否则页面能开但接口会失败。
3. 联调结束后关闭 ngrok，避免误把临时地址当正式环境使用。
4. 可通过 ngrok 本地控制台 `http://127.0.0.1:4040` 查看请求明细，便于排查。

---

## 4. 场景二：后端断点调试 — 让请求打到本地 JAR

### 4.1 适用情况

- 逻辑复杂，Knife4j 手动构造请求、查库成本高。
- 希望 **真实前端页面发请求**，在 IDE 里对本地微服务 **打断点** 调试。

### 4.2 为什么不能只启动本地服务？

本地服务可以注册到 Nacos，但 **服务器上的网关实例无法访问你电脑的局域网 IP**。负载均衡仍可能把请求打到服务器上的旧实例，本地断点不会命中。

解决思路：**让 Nacos 里该服务的「对外地址」指向 ngrok 公网域名**，网关通过 HTTPS:443 把流量转到 ngrok，再隧道到本机端口。

```
浏览器 → 服务器网关 (:3000)
           → Nacos 解析服务地址为 ngrok 域名 (:443)
           → ngrok 隧道
           → localhost:本机微服务端口
           → IDE 断点
```

### 4.3 前置工作清单

| 步骤 | 操作 | 目的 |
|------|------|------|
| 1 | 本机启动目标微服务（Debug 模式） | 断点生效 |
| 2 | 本机 `ngrok http <微服务端口>` | 获得公网 HTTPS 入口 |
| 3 | 修改该服务 `bootstrap.yaml` 中 Nacos 注册 IP/端口 | 让网关找到 ngrok |
| 4 | **下线 Nacos 上服务器同名实例** | 避免请求仍打到服务器 |

### 4.4 配置 Nacos 服务发现（bootstrap.yaml）

以 **hongguang-scheduling** 为例，在 `bootstrap.yaml` 中增加或调整 `discovery` 段（**域名换成你当前 ngrok 会话的实际地址**）：

```yaml
spring:
  profiles:
    active: dev
  application:
    name: hongguang-scheduling
  cloud:
    nacos:
      discovery:
        ip: <your-subdomain>.ngrok-free.dev   # ngrok 分配的域名，不含 https://
        port: 443                                      # ngrok HTTPS 对外端口
        secure: true                                   # 使用 HTTPS
      config:
        server-addr: nacos-register:8848
        file-extension: yaml
        prefix: ${spring.application.name}
        enabled: true
        group: HONGGUANG_GROUP
        namespace: hongguang
```

**字段说明：**

| 配置项 | 含义 |
|--------|------|
| `discovery.ip` | 注册到 Nacos 的「主机名」，填 ngrok 域名 |
| `discovery.port` | 对外端口，HTTPS 隧道一般为 `443` |
| `discovery.secure` | `true` 表示网关用 HTTPS 访问该实例 |

修改后 **重启本地微服务**，在 Nacos 控制台确认实例 IP 为 ngrok 域名、端口为 443。

### 4.5 下线服务器上的同名实例

1. 登录 Nacos 控制台 → 命名空间 **hongguang** → 服务列表。
2. 找到对应服务名（如 `hongguang-scheduling`）。
3. 将 **服务器上** 的实例设为下线或临时停止该 JAR，确保流量只到本地。

> **重要**：调试结束后务必 **恢复服务器实例** 并 **还原本地 bootstrap.yaml**，否则会影响测试 / 生产环境。

### 4.6 启动 ngrok（后端）

假设本地微服务监听 **8080**（以实际 `server.port` 为准）：

```bash
ngrok http 8080
```

记下 `Forwarding` 行中的 `https://xxx.ngrok-free.dev`，与 `bootstrap.yaml` 里 `discovery.ip` 保持一致（仅域名部分）。

### 4.7 验证流程

1. 前端照常访问服务器地址（:93）或本地 dev server。
2. 触发会调用目标微服务的业务操作。
3. 在 IDE 中应命中断点；ngrok Web Interface（`:4040`）可看到转发的 HTTP 请求。

---

## 5. 常见问题

### 5.1 ngrok 域名变了怎么办？

免费版重启 ngrok 会换域名。需：

1. 更新 `bootstrap.yaml` 中 `discovery.ip`；
2. 重启本地微服务；
3. 在 Nacos 确认新实例注册成功。

### 5.2 请求仍打到服务器，断点不生效

- 检查 Nacos 是否仍有 **online** 的服务器实例 → 全部下线或停用。
- 检查本地服务注册的 IP 是否为当前 ngrok 域名、端口是否为 443。
- 网关缓存：稍等片刻或重启网关（需与运维协调，慎用）。

### 5.3 前端 ngrok 能开，但接口 401 / 502

- 401：Token / 登录态问题，与 ngrok 无关，先在同一网络下用 localhost 复现。
- 502：ngrok 未启动、本地 dev server 已退出，或 ngrok 映射端口与 dev server 不一致。
### 5.4 ngrok安全拦截
- 对于GET请求，ngrok会在浏览器拦截，解决方案是将请求改为POST方法

---

## 6. 联调结束后的收尾

请按顺序执行，避免遗留影响环境：

1. 停止本机 ngrok 进程（`Ctrl+C`）。
2. 停止本地 Debug 微服务。
3. **还原** `bootstrap.yaml` 中 `discovery.ip` / `port` / `secure`（或恢复为默认，删除临时覆盖项）。
4. 在 Nacos **重新上线** 服务器上的微服务实例。
5. 通知测试人员临时 ngrok 地址已失效。

---

## 7. 小结

| 场景 | ngrok 命令示例 | 额外配置 |
|------|----------------|----------|
| 前端快速验证 | `ngrok http 80`（或 dev 实际端口） | 无；把 HTTPS 地址发给测试即可 |
| 后端断点调试 | `ngrok http 8080`（或微服务端口） | `bootstrap.yaml` 注册 ngrok 域名 + 下线服务器实例 |

ngrok 适合 **短期、小范围** 联调。正式发布仍应走标准流程：前端 `build:prod` 上传 `dist`，后端部署 JAR 并由 Nacos 注册服务器内网地址。