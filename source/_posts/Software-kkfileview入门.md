---
title: kkFileView 文件在线预览服务入门指南
date: 2026-06-16 16:00:00
updated: 2026-06-16 18:00:00
categories:
  - Software
tags:
  - kkFileView
  - 文件预览
  - 在线预览
---

本文介绍 kkFileView 文件在线预览服务的基本概念、配置和使用方法。

---

## 1. 什么是 kkFileView

kkFileView 是一个基于 Spring Boot 的文件在线预览服务，支持多种文件格式的在线预览，包括：

| 文件类型 | 支持格式 |
|----------|----------|
| **Office** | doc, docx, xls, xlsx, ppt, pptx |
| **PDF** | pdf |
| **图片** | jpg, jpeg, png, gif, bmp |
| **文本** | txt, html, xml, json, md 等 |
| **多媒体** | mp3, wav, mp4, flv |

---

## 2. 快速开始

### 2.1 启动服务

**Windows：**
```bash
cd kkFileView-4.0.0/bin
startup.bat
```

**Linux：**
```bash
cd kkFileView-4.0.0/bin
./startup.sh
```

服务启动后，访问 http://localhost:8012 即可看到预览界面。

### 2.2 预览文件

通过 URL 参数 `url` 传递文件地址：

```
# 预览本地文件
http://localhost:8012/onlinePreview?url=http://127.0.0.1:8080/group1/default/20260616/10/22/2/test.pdf

# 预览远程文件（需要进行 Base64 编码）
http://localhost:8012/onlinePreview?url=aHR0cDovLzEyNy4wLjAuMTo4MDgwL2dyb3VwMS9kZWZhdWx0LzIwMjYwNjE2LzEwLzIyLzIvdGVzdC5wZGY=
```

### 2.3 URL 编码说明

文件 URL 需要进行 **Base64 编码**：

```javascript
// JavaScript 示例
var fileUrl = 'http://127.0.0.1:8080/group1/default/20260616/10/22/2/test.pdf';
var encodedUrl = btoa(fileUrl).replace(/\r\n/g, '');
var previewUrl = 'http://localhost:8012/onlinePreview?url=' + encodedUrl;
```

---

## 3. 核心配置

配置文件位于 `config/application.properties`：

### 3.1 端口配置

```properties
# 服务端口（默认 8012）
server.port = 8012
```

### 3.2 Office 转换服务

```properties
# office转换服务的进程数，默认开启两个进程
office.plugin.server.ports = 2001,2002

# office 转换服务 task 超时时间，默认五分钟
office.plugin.task.timeout = 5m
```

### 3.3 缓存配置

```properties
# 缓存实现类型：default(RocksDB)、redis、jdk
cache.type = jdk

# 是否启用缓存
cache.enabled = true

# 缓存自动清理时间（凌晨3点）
cache.clean.cron = 0 0 3 * * ?
```

### 3.4 水印配置

```properties
# 水印内容（为空则不显示水印）
watermark.txt = 

# 水印字体和大小
watermark.font = 微软雅黑
watermark.fontsize = 18px

# 水印透明度（0.005-1）
watermark.alpha = 0.2
```

### 3.5 预览类型配置

```properties
# office类型文档(word ppt)样式：image 或 pdf
office.preview.type = image

# 是否关闭office预览切换开关
office.preview.switch.disabled = false

# 是否禁止下载转换生成的pdf文件
pdf.download.disable = true
```

---

## 4. 目录结构

```
kkFileView-4.0.0/
├── bin/
│   ├── kkFileView-4.0.0.jar    # 主程序
│   └── startup.bat              # Windows 启动脚本
├── config/
│   ├── application.properties   # 配置文件
│   └── freemarker_implicit.ftl  # Freemarker 模板
├── file/                        # 文件存储目录
├── log/                         # 日志目录
│   └── kkFileView.log           # 服务日志
└── windows-office/              # 内置 LibreOffice
    └── program/                 # Office 程序文件
```

---

## 5. 前端集成示例

### 5.1 基础集成

```html
<!DOCTYPE html>
<html>
<head>
    <title>文件预览</title>
</head>
<body>
    <button onclick="previewFile()">预览文件</button>
    
    <script>
        function previewFile() {
            var fileUrl = 'http://127.0.0.1:8080/group1/default/20260616/10/22/2/test.pdf';
            var encodedUrl = btoa(fileUrl).replace(/\r\n/g, '');
            var previewUrl = 'http://localhost:8012/onlinePreview?url=' + encodedUrl;
            window.open(previewUrl, '_blank');
        }
    </script>
</body>
</html>
```

### 5.2 在 gofastdfs 上传页面中集成预览

```javascript
// 上传成功后显示预览按钮
if (result.data && result.data.url) {
    var previewBtn = document.createElement('button');
    previewBtn.textContent = '预览此文件';
    previewBtn.onclick = function() {
        var url = result.data.url.split('?')[0];
        var encodedUrl = btoa(url).replace(/\r\n/g, '');
        window.open('http://localhost:8012/onlinePreview?url=' + encodedUrl, '_blank');
    };
    document.getElementById('uploadResult').appendChild(previewBtn);
}
```

---

## 6. 常见问题

### Q1：Office 文件预览失败？

**可能原因：**
- LibreOffice 进程未正确启动
- 文件路径包含中文或特殊字符
- 文件大小超过限制

**解决方案：**
- 检查 `office.plugin.server.ports` 端口是否被占用
- 确保文件 URL 正确编码
- 增大 `spring.servlet.multipart.max-file-size` 配置

### Q2：预览页面加载缓慢？

**原因：** 首次预览需要进行格式转换，耗时较长。

**解决方案：**
- 开启缓存功能（`cache.enabled = true`）
- 使用 Redis 缓存替代默认缓存

### Q3：如何禁止文件下载？

**方法：** 修改配置文件：

```properties
pdf.download.disable = true
```

### Q4：如何添加水印？

**方法：** 修改配置文件：

```properties
watermark.txt = 内部文件，严禁外泄
watermark.font = 微软雅黑
watermark.fontsize = 18px
watermark.color = black
watermark.alpha = 0.2
```

---

## 7. 支持的文件格式

| 类型 | 格式 |
|------|------|
| **Word** | doc, docx, dot, dotx |
| **Excel** | xls, xlsx, xlt, xltx |
| **PowerPoint** | ppt, pptx, pps, ppsx |
| **PDF** | pdf |
| **图片** | jpg, jpeg, png, gif, bmp, tiff |
| **文本** | txt, html, htm, xml, json, md, java, py, sql |
| **多媒体** | mp3, wav, mp4, flv |

---

## 8. 总结

| 功能 | 说明 |
|------|------|
| **多格式支持** | 支持 Office、PDF、图片、文本等多种格式 |
| **在线预览** | 无需下载，直接在浏览器中查看 |
| **格式转换** | 自动将 Office 文件转换为图片或 PDF |
| **缓存机制** | 支持多种缓存策略，提升预览速度 |
| **水印功能** | 支持自定义水印内容和样式 |

kkFileView 是一个轻量级的文件预览服务，适合集成到各类文件管理系统中。

---

## 9. 参考链接

- [kkFileView GitHub 仓库](https://github.com/kekingcn/kkFileView)
- [kkFileView 官方文档](https://kkfileview.keking.cn/)
