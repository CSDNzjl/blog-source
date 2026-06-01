---
title: 虹光项目：服务重启钉钉实时监控
date: 2026-06-01 11:00:00
updated: 2026-06-01 11:00:00
categories:
  - Kocel
tags:
  - Kocel
  - 虹光
  - 钉钉
  - 运维
  - Shell
cover: /images/hongguang-logo.png
---

本文说明如何在 **hongguang（虹光铸造全生命周期管理系统）** 服务器上，通过 **钉钉自定义机器人 Webhook**，在微服务重启时自动通知群内同事，避免测试误判、依赖服务中断无人知晓、或未拉最新代码就重启等问题。

> **适用读者**：后端开发、实施与运维同事。  
> **前置知识**：了解服务器 JAR 部署与 `restart.sh` 用法，可参考 [虹光项目：服务器部署架构与从零搭建指南](/2026/05/29/虹光项目：服务器部署架构与从零搭建指南/) 第 5 节。

---

## 1. 为什么需要重启通知

多人协作测试 / 开发时，单点重启微服务容易引发以下问题：

| 问题 | 表现 | 通知的作用 |
|------|------|------------|
| 测试误判 | 开发重启某服务，实施人员以为业务代码有 Bug | 群内提前告知「服务即将中断 / 已恢复」 |
| 依赖链断裂 | A 服务重启导致 B 服务调用失败，其他开发不知情 | @所有人 及时同步，避免无效排查 |
| 代码版本不一致 | 他人未拉最新代码就重启，环境状态与预期不符 | 操作人、时间一目了然，便于追溯 |

**目标流程：**

```
开发人员执行 ./xxx/restart.sh
        │
        ├─► ① 钉钉：「即将重启」(@所有人)
        │
        ├─► ② stop → start（原有 common.sh 逻辑）
        │
        ├─► ③ 钉钉：「重启完成」(@所有人)
        │
        └─► ④ tail -f logs/console.log（跟随日志）
```

通知失败 **不会阻断** 重启主流程，避免因网络抖动导致服务起不来。

---

## 2. 钉钉机器人配置

### 2.1 创建自定义机器人

1. 打开钉钉，进入项目协作群（建议单独建「虹光-服务重启通知」群）。
2. 群设置 → **智能群助手** → **添加机器人** → **自定义**（通过 Webhook 接入）。
3. 安全设置建议勾选 **自定义关键词**，填入例如：`服务重启`（与通知文案中的关键词一致）。
4. 创建完成后复制 **Webhook 地址**，格式如下：

```text
https://oapi.dingtalk.com/robot/send?access_token=<YOUR_ACCESS_TOKEN>
```

> **安全提醒**：`access_token` 等同于机器人密钥，**不要提交到 Git、不要写进公开文档**。下文脚本通过环境变量或服务器本地配置注入，示例代码均使用占位符。

### 2.2 在服务器上配置 Token（推荐）

在部署用户（如 `ifom`）的 `~/.bashrc` 或各服务 `app.env` 中设置：

```bash
export DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=<YOUR_ACCESS_TOKEN>"
```

`notify.sh` 会优先读取环境变量 `DINGTALK_WEBHOOK`，未设置时才使用脚本内默认值（生产环境建议 **只使用环境变量**，脚本内留空或删除默认 Token）。

---

## 3. 目录与文件位置

与现有部署结构一致（`/home/ifom/hongguang/`）：

```text
/home/ifom/hongguang/
├── bin/
│   ├── common.sh          # 已有：stop / start 公共逻辑
│   └── notify.sh          # 新增：钉钉通知模块（本文提供）
├── gateway/
│   └── restart.sh         # 各微服务目录下均有 restart.sh
├── scheduling/
│   └── restart.sh         # 示例：排产服务
├── auth-server/
│   └── restart.sh
└── ...
```

| 文件 | 职责 |
|------|------|
| `bin/notify.sh` | 定义 `send_dingtalk_notify`，**仅供 restart.sh 调用** |
| `各服务/restart.sh` | 重启前/后调用通知，再执行 stop → start → tail 日志 |

---

## 4. 新增通知模块：`bin/notify.sh`

在服务器创建 `/home/ifom/hongguang/bin/notify.sh`：

```bash
#!/usr/bin/env bash
# /home/ifom/hongguang/bin/notify.sh
# 本项目专用的钉钉通知模块
# 仅供 restart.sh 调用，不要直接执行

set -euo pipefail

# ================= 配置区域 =================
# 优先使用环境变量 DINGTALK_WEBHOOK；未设置时使用下方占位（生产请改为 export 注入）
: "${DINGTALK_WEBHOOK:=https://oapi.dingtalk.com/robot/send?access_token=<YOUR_ACCESS_TOKEN>}"

# 发送钉钉通知
# 参数: $1=状态(stop/finish), $2=详情消息
send_dingtalk_notify() {
    local status_type="$1"
    local msg_detail="$2"

    local svc_name="${SERVICE_NAME:-UnknownService}"
    local current_time
    current_time=$(date "+%Y-%m-%d %H:%M:%S")
    local operator
    operator=$(whoami)

    local title=""
    local text=""

    case "$status_type" in
        "stop")
            title="⏳ 服务即将重启 - ${svc_name}"
            text="# 🚨 **服务重启通知**\n\n- **状态**: 正在停止服务\n- **服务**: ${svc_name}\n- **操作人**: ${operator}\n- **时间**: ${current_time}\n- **详情**: ${msg_detail}\n\n> @所有人 请知悉，服务即将中断"
            ;;
        "finish")
            title="✅ 服务重启完成 - ${svc_name}"
            text="# ✅ **服务重启完成**\n\n- **状态**: 服务已启动\n- **服务**: ${svc_name}\n- **操作人**: ${operator}\n- **时间**: ${current_time}\n- **详情**: ${msg_detail}\n\n> @所有人 服务已恢复，请验证业务是否正常"
            ;;
        *)
            return 0
            ;;
    esac

    local payload
    payload=$(cat <<EOF
{
    "msgtype": "markdown",
    "markdown": {
        "title": "${title}",
        "text": "$(echo "$text" | sed 's/\$/\\$/g' | sed 's/"/\\"/g')"
    },
    "at": {
        "isAtAll": true
    }
}
EOF
)

    if curl -s -X POST "$DINGTALK_WEBHOOK" \
        -H 'Content-Type: application/json' \
        -d "$payload" > /dev/null 2>&1; then
        echo "[INFO] [钉钉] 通知发送成功：${title}"
    else
        echo "[WARN] [钉钉] 通知发送失败 (可能是网络问题)，但将继续执行..." >&2
    fi
}
```

赋予可执行权限（可选，因该文件仅被 `source`，非直接执行）：

```bash
chmod +x /home/ifom/hongguang/bin/notify.sh
```

**消息模板说明：**

| `status_type` | 标题 | 触发时机 |
|---------------|------|----------|
| `stop` | ⏳ 服务即将重启 | `service_stop` 之前 |
| `finish` | ✅ 服务重启完成 | `service_start` 之后 |

两条消息均 `@所有人`，Markdown 正文包含服务名、操作人、时间戳。

---

## 5. 改造各服务的 `restart.sh`

以 **scheduling（排产）** 为例，路径：`/home/ifom/hongguang/scheduling/restart.sh`。  
其他微服务（`gateway`、`auth-server`、`form` 等）按同样方式改造各自目录下的 `restart.sh`。

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SERVICE_ROOT="$(cd "$(dirname "$0")" && pwd)"

# 自动取当前目录名作为服务名（如 scheduling、gateway）
SERVICE_NAME="$(basename "$SERVICE_ROOT")"

# 1. 加载公共脚本
if [[ -f "${ROOT}/../bin/common.sh" ]]; then
    source "${ROOT}/../bin/common.sh"
else
    echo "[ERROR] 未找到 common.sh 脚本，请检查路径。" >&2
    exit 1
fi

# 2. 加载钉钉通知模块（可选，缺失不影响重启）
NOTIFY_FILE="${ROOT}/../bin/notify.sh"
if [[ -f "$NOTIFY_FILE" ]]; then
    source "$NOTIFY_FILE"
    echo "[INFO] 已加载钉钉通知模块。"
else
    echo "[WARN] 未找到 notify.sh，将跳过钉钉通知，但服务重启将继续执行。" >&2
fi

# --- 步骤 1: 发送「即将重启」通知 ---
if declare -f send_dingtalk_notify > /dev/null 2>&1; then
    send_dingtalk_notify "stop" "服务 ${SERVICE_NAME} 正在进行重启操作，期间服务将不可用。"
else
    echo "[INFO] 跳过重启前通知 (函数未定义)。"
fi

# --- 步骤 2: 停止并启动 ---
echo "[INFO] 开始执行服务停止与启动..."
service_stop "$SERVICE_NAME" "$SERVICE_ROOT"
service_start "$SERVICE_NAME" "$SERVICE_ROOT" ""
echo "[INFO] 服务重启命令执行完毕。"

# --- 步骤 3: 发送「重启完成」通知 ---
if declare -f send_dingtalk_notify > /dev/null 2>&1; then
    send_dingtalk_notify "finish" "服务 ${SERVICE_NAME} 已重新启动，请验证业务是否正常。"
else
    echo "[INFO] 跳过重启后通知 (函数未定义)。"
fi

# --- 步骤 4: 跟随控制台日志 ---
LOG_FILE="${SERVICE_ROOT}/logs/console.log"
if [[ -f "$LOG_FILE" ]]; then
    tail -f "$LOG_FILE"
else
    echo "[ERROR] 日志文件 ${LOG_FILE} 不存在，无法跟随日志。" >&2
    exit 1
fi
```

### 5.1 新建脚本时的权限

若 `restart.sh` 为新建文件，需赋予可执行权限：

```bash
cd /home/ifom/hongguang/scheduling
chmod +x ./restart.sh
```

### 5.2 批量推广到其他服务

建议按以下顺序在各服务目录替换 / 合并 `restart.sh`：

1. `gateway`（影响面最大，优先打通通知链路）
2. `auth-server`
3. 各业务模块（`form`、`smelt`、`scheduling` 等）

每改一个服务，执行一次 `./restart.sh` 并在钉钉群确认收到两条消息。

---

## 6. 验证与测试

### 6.1 快速自检清单

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 确认 `DINGTALK_WEBHOOK` 已 export 或 notify.sh 内 Token 正确 | `echo $DINGTALK_WEBHOOK` 有值 |
| 2 | 确认机器人关键词与安全设置 | 消息含「服务重启」等关键词 |
| 3 | 执行 `./scheduling/restart.sh`（示例） | 终端打印「通知发送成功」 |
| 4 | 查看钉钉群 | 先后收到「即将重启」「重启完成」两条 @所有人 消息 |
| 5 | 实施同事验证业务 | 重启窗口内接口短暂不可用属正常 |

### 6.2 单独测试 Webhook（可选）

```bash
curl -X POST "$DINGTALK_WEBHOOK" \
  -H 'Content-Type: application/json' \
  -d '{"msgtype":"text","text":{"content":"服务重启 - Webhook 连通性测试"}}'
```

钉钉群收到测试消息后，再接入完整 `restart.sh` 流程。

---

## 7. 常见问题

### 7.1 钉钉收不到消息

| 可能原因 | 处理方式 |
|----------|----------|
| Token 错误或过期 | 在钉钉群重新创建机器人，更新 `DINGTALK_WEBHOOK` |
| 未配置关键词 | 机器人安全设置中添加「服务重启」等关键词 |
| 服务器无法访问外网 | `curl -I https://oapi.dingtalk.com` 检查连通性 |
| `notify.sh` 路径不对 | 确认 `../bin/notify.sh` 相对各服务目录可访问 |

### 7.2 通知失败但服务仍重启

这是 **刻意设计**：`send_dingtalk_notify` 内 curl 失败只打 `[WARN]`，不 `exit`，避免通知网络问题拖垮运维操作。

### 7.3 服务名显示不对

`SERVICE_NAME` 取自 **restart.sh 所在文件夹名**（如 `scheduling`）。若需显示 Nacos 注册名（如 `hongguang-scheduling`），可在 `restart.sh` 中改为：

```bash
SERVICE_NAME="hongguang-scheduling"
```

或在各目录 `app.env` 中定义 `SERVICE_NAME` 并在脚本开头读取。

### 7.4 误 @所有人 太频繁

若仅需通知开发群、不打扰全员，将 `notify.sh` 中 `"isAtAll": true` 改为 `false`，并配置 `"atMobiles": ["138xxxx"]` 指定手机号。

---

## 8. 使用规范（给全员的约定）

1. **重启前**：确认已拉取最新代码、JAR 已替换完毕；非必要避免业务高峰重启 **gateway / auth-server**。
2. **重启后**：在钉钉回复一条简要验证结果（如「排产列表接口正常」），方便他人判断是否可继续测试。
3. **依赖关系**：若改动涉及网关路由或认证，重启顺序仍遵循 `service-order.conf`（网关 → 认证 → 业务）。
4. **Token 轮换**：机器人泄露或人员变动时，在钉钉侧停用旧机器人并更新服务器环境变量，**勿在聊天记录中粘贴完整 Webhook**。

---

## 9. 小结

| 组件 | 路径 | 作用 |
|------|------|------|
| 钉钉机器人 | 群设置中创建 | 提供 Webhook 接收 Markdown 消息 |
| `bin/notify.sh` | 公共通知模块 | `send_dingtalk_notify stop/finish` |
| `*/restart.sh` | 各微服务目录 | 重启前后发通知 + 原有 stop/start |

按本文配置后，任意同事执行 `./xxx/restart.sh` 都会自动同步重启状态，减少联调过程中的信息不对称。新同事首次部署建议与熟悉服务器的同事 **结对操作一次**，确认钉钉群、Token 与脚本路径均正确后再独立使用。
