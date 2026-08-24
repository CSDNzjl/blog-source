---
title: gofastdfs 入门指南
date: 2026-06-16 14:00:00
updated: 2026-06-16 18:00:00
categories:
  - Software
tags:
  - gofastdfs
  - 文件存储
  - 分布式存储
---

本文介绍 gofastdfs 的基本概念、核心功能及使用方法，基于实际部署和调试经验整理。

---

## 1. 什么是 gofastdfs

gofastdfs 是一个用 Go 语言实现的轻量级分布式文件系统，具有以下特点：

| 特性 | 说明 |
|------|------|
| **轻量级** | 单二进制文件，无外部依赖 |
| **分布式** | 支持集群部署，自动同步 |
| **文件去重** | 基于 MD5/SHA1 自动去重，节省存储空间 |
| **时间分层** | 按日期自动组织文件存储路径 |
| **Web 上传** | 内置 Web 界面，方便调试 |

---

## 2. 快速开始

### 2.1 启动服务

```bash
# Windows
fileserver.exe server

# Linux
./fileserver server
```

服务启动后，访问 http://localhost:8080 即可看到管理界面。

### 2.2 上传文件

通过 Web 界面或 API 上传：

```bash
# 使用 curl 上传
curl -X POST http://localhost:8080/group1/upload \
  -F "file=@test.jpg" \
  -F "output=json"
```

### 2.3 响应示例

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "url": "http://127.0.0.1:8080/group1/default/20260616/10/22/2/test.jpg",
    "path": "/group1/default/20260616/10/22/2/test.jpg",
    "md5": "fbb83430da210d7430eaea0cd9e654b2",
    "size": 16154,
    "scene": "default"
  }
}
```

### 2.4 前端上传页面（upload.html）

创建一个简单的 HTML 上传页面：

```html
<!DOCTYPE html>
<html>
<head><title>文件上传</title></head>
<body>
    <h1>文件上传到 gofastdfs</h1>
    
    <form id="uploadForm">
        <input type="file" name="file" id="fileInput" required>
        <br><br>
        <label>场景: <input type="text" name="scene" value="default" id="sceneInput"></label>
        <br><br>
        <button type="submit">上传</button>
    </form>
    
    <h2>上传结果</h2>
    <pre id="uploadResult"></pre>
    
    <hr>
    
    <h2>删除文件</h2>
    <form id="deleteForm">
        <label>文件路径: <input type="text" name="deletePath" id="deletePathInput" placeholder="如: default/20260616/10/22/2/xxx.png" required></label>
        <br><br>
        <label>MD5值: <input type="text" name="deleteMd5" id="deleteMd5Input" placeholder="上传时返回的MD5值"></label>
        <br><br>
        <button type="submit">删除文件</button>
    </form>
    
    <h2>删除结果</h2>
    <pre id="deleteResult"></pre>

    <script>
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            var fileInput = document.getElementById('fileInput');
            var sceneInput = document.getElementById('sceneInput').value || 'default';
            
            if (!fileInput.files[0]) {
                alert('请选择文件');
                return;
            }
            
            var formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('output', 'json');
            // 不指定 path，让服务器端自动处理路径和去重
            formData.append('scene', sceneInput);
            
            try {
                var response = await fetch('http://127.0.0.1:8080/group1/upload', {
                    method: 'POST',
                    body: formData
                });
                
                var result = await response.json();
                document.getElementById('uploadResult').textContent = JSON.stringify(result, null, 2);
                
                // 如果上传成功，自动填充删除表单
                if (result.data && result.data.path) {
                    var filePath = result.data.path;
                    // 去掉 /group1/ 前缀（删除接口不需要 group 前缀）
                    filePath = filePath.replace(/^\/group\d+\//, '');
                    document.getElementById('deletePathInput').value = filePath;
                }
                if (result.data && result.data.md5) {
                    document.getElementById('deleteMd5Input').value = result.data.md5;
                }
            } catch (err) {
                document.getElementById('uploadResult').textContent = '上传失败: ' + err.message;
            }
        });
        
        // 删除文件功能
        document.getElementById('deleteForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            var deletePath = document.getElementById('deletePathInput').value.trim();
            var deleteMd5 = document.getElementById('deleteMd5Input').value.trim();
            
            if (!deletePath) {
                alert('请输入文件路径');
                return;
            }
            
            // 确保路径格式正确（去掉开头的斜杠）
            deletePath = deletePath.replace(/^\//, '');
            
            if (!confirm('确定要删除该文件吗？此操作不可恢复！')) {
                return;
            }
            
            var formData = new FormData();
            formData.append('path', deletePath);
            
            try {
                var response = await fetch('http://127.0.0.1:8080/group1/delete', {
                    method: 'POST',
                    body: formData
                });
                
                var result = await response.json();
                document.getElementById('deleteResult').textContent = JSON.stringify(result, null, 2);
            } catch (err) {
                document.getElementById('deleteResult').textContent = '删除失败: ' + err.message;
            }
        });
    </script>
</body>
</html>
```

**使用方法：**
1. 将上述代码保存为 `upload.html`
2. 放置在 gofastdfs 服务的静态文件目录或通过 HTTP 服务器访问
3. 浏览器打开即可上传和删除文件

---

## 3. 文件存储路径结构

gofastdfs 采用时间分层 + 场景 + 集群节点的路径策略：

```
/group1/default/20260616/10/22/2/test.jpg
│      │        │         │   │   │
│      │        │         │   │   └── peer_id（集群节点ID）
│      │        │         │   └── 分钟（0-59）
│      │        │         └── 小时（0-23）
│      │        └── 日期（YYYYMMDD）
│      └── 场景（scene）
└── 组号（group）
```

### 路径各部分说明

| 层级 | 示例 | 说明 |
|------|------|------|
| group | `group1` | 集群分组标识 |
| scene | `default` | 场景名称，支持多场景隔离 |
| 日期 | `20260616` | 上传日期 |
| 小时 | `10` | 上传小时 |
| 分钟 | `22` | 上传分钟 |
| peer_id | `2` | 集群节点标识 |

---

## 4. 文件去重机制

### 4.1 去重原理

gofastdfs 通过文件内容的 MD5 值进行去重：

```
上传流程（开启去重）：
1. 接收文件 → 计算 MD5
2. 查询数据库是否存在该 MD5
3. 如果存在 → 返回已存在的文件路径（去重成功）
4. 如果不存在 → 保存文件 + 记录到数据库
```

### 4.2 去重配置

在 `conf/cfg.json` 中配置：

```json
{
  "enable_distinct_file": true,  // 是否开启去重
  "file_sum_arithmetic": "md5"   // 去重算法：md5 或 sha1
}
```

### 4.3 去重的影响

| 状态 | 存储空间 | 删除功能 | 上传速度 |
|------|----------|----------|----------|
| 开启去重 | 节省空间 | 需要数据库 | 稍慢（需计算 MD5） |
| 关闭去重 | 占用更多空间 | 无法通过 API 删除 | 更快 |

> **注意：** 关闭去重后，文件不会记录到数据库，导致删除接口无法使用。

---

## 5. 文件删除

### 5.1 API 删除

```bash
curl -X POST http://localhost:8080/group1/delete \
  -F "path=default/20260616/10/22/2/test.jpg"
```

### 5.2 响应示例

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "path": "default/20260616/10/22/2/test.jpg",
    "status": "deleted"
  }
}
```

### 5.3 删除失败原因

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `md5 unvalid` | 文件未记录到数据库 | 确保开启去重后上传的文件 |
| `path not found` | 文件路径错误 | 检查路径格式，不含 `/group1/` 前缀 |

---

## 6. 核心配置说明

```json
{
  "addr": ":8080",                    // 监听端口
  "peer_id": "2",                     // 集群节点ID（0-9）
  "host": "http://127.0.0.1:8080", // 本机地址
  "group": "group1",                  // 组名
  "enable_distinct_file": true,       // 开启文件去重
  "rename_file": false,               // 是否自动重命名
  "enable_web_upload": true,          // 启用 Web 上传
  "admin_ips": ["127.0.0.1"],        // 管理 IP 白名单
  "default_scene": "default"          // 默认场景
}
```

### 关键配置项

| 配置项 | 作用 | 默认值 |
|--------|------|--------|
| `enable_distinct_file` | 控制文件去重和数据库记录 | `true` |
| `rename_file` | 文件重名时自动添加前缀 | `false` |
| `admin_ips` | 允许管理操作的 IP 列表 | `["127.0.0.1"]` |
| `peer_id` | 集群内唯一标识 | 自动生成 |

---

## 7. 常见问题

### Q1：为什么相同 MD5 的文件没有被去重？

**可能原因：**
- 手动指定了不同的 `path` 参数，导致文件保存到不同位置
- `enable_distinct_file` 配置为 `false`
- 服务未重启，配置未生效

**解决方案：** 上传时不指定 `path` 参数，让服务器自动处理。

### Q2：删除文件时报错 `md5 unvalid`？

**原因：** 文件上传时去重功能未开启，导致文件信息未记录到数据库。

**解决方案：** 确保 `enable_distinct_file: true`，重新上传文件后再删除。

### Q3：如何禁用文件去重？

**方法：** 修改配置并重启服务：

```json
"enable_distinct_file": false
```

**注意：** 禁用后无法使用 API 删除文件，需手动操作文件系统。

### Q4：为什么配置修改后不生效？

gofastdfs 配置文件修改后需要**重启服务**才能生效：

```bash
# Windows
Stop-Process -Name "fileserver" -Force
fileserver.exe server
```

---

## 8. 目录结构

```
gofastdfs/
├── fileserver.exe       # 主程序
├── conf/
│   └── cfg.json        # 配置文件
├── data/
│   ├── fileserver.db/  # LevelDB 数据库（存储文件元数据）
│   ├── log.db/         # 日志数据库
│   └── stat.json       # 统计信息
├── files/              # 文件存储目录
│   └── default/        # 默认场景
└── log/
    ├── fileserver.log  # 服务日志
    └── access.log      # 访问日志
```

---

## 9. 总结

| 功能 | 说明 |
|------|------|
| **文件上传** | 支持 Web 界面和 API，自动生成时间分层路径 |
| **文件去重** | 基于 MD5 自动去重，相同内容只存储一份 |
| **文件删除** | 需要开启去重功能，通过 API 删除 |
| **配置热更新** | 不支持，修改配置需重启服务 |

gofastdfs 适合作为轻量级文件存储服务，配置简单，部署方便。如需完整的文件管理功能，建议保持去重功能开启。

---

## 10. 参考链接

- [gofastdfs GitHub 仓库](https://github.com/sjqzhang/go-fastdfs)
- [gofastdfs 官方文档](https://gofastdfs.com/)
