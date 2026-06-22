---
title: 虹光项目：Flyway 数据库版本管理指南
date: 2026-06-22 10:00:00
updated: 2026-06-22 10:00:00
categories:
  - Kocel
tags:
  - Kocel
  - 虹光
  - Flyway
  - MySQL
  - Spring Boot
cover: /images/hongguang-logo.png
---

本文整合 Flyway 通用入门知识、**hongguang（虹光铸造全生命周期管理系统）** 落地配置，以及排产模块（`hongguang-scheduling`）试点过程中踩过的坑，用于指导全模块数据库变更的统一管理。

> **适用读者**：后端开发、DBA、实施与运维同事。  
> **前置知识**：了解虹光微服务架构与 Nacos 配置方式，可参考 [虹光项目：服务器部署架构与从零搭建指南](/2026/05/29/虹光项目：服务器部署架构与从零搭建指南/)。

---

## 目录

1. [Flyway 是什么](#1-flyway-是什么)
2. [虹光项目现状与目标](#2-虹光项目现状与目标)
3. [技术栈与依赖说明](#3-技术栈与依赖说明)
4. [完整配置流程（新模块接入）](#4-完整配置流程新模块接入)
5. [SQL 脚本命名规范](#5-sql-脚本命名规范)
6. [执行逻辑与历史表机制](#6-执行逻辑与历史表机制)
7. [已有数据库接入（Baseline）](#7-已有数据库接入baseline)
8. [虹光项目踩坑记录（必读）](#8-虹光项目踩坑记录必读)
9. [绝对禁止的操作](#9-绝对禁止的操作)
10. [配置模板速查](#10-配置模板速查)

---

## 1. Flyway 是什么

Flyway 是一个开源的**数据库版本控制工具**（Database Versioning Tool）。


| 维度   | 说明                                                     |
| ---- | ------------------------------------------------------ |
| 核心作用 | 管理数据库结构变更（Schema Migration），确保开发、测试、生产环境结构一致           |
| 工作原理 | 扫描 `db/migration/` 下的 SQL 脚本，对比历史表中的执行记录，按版本顺序执行未运行的脚本 |
| 最大优势 | 自动化增量更新，无需人工记「哪个环境跑了哪个脚本」                              |


**与当前做法的区别：**


| 旧方式                                            | Flyway 方式                        |
| ---------------------------------------------- | -------------------------------- |
| SQL 放在 `src/main/resources/db/` 下，靠 DBA/开发手动执行 | SQL 放在 `db/migration/`，服务启动时自动执行 |
| 文件名随意（如 `storage_ddl.sql`）                     | 文件名严格遵循 `V版本__描述.sql`            |
| 无执行记录，易漏跑、重复跑                                  | `{模块}_flyway_history` 表记录每次执行    |


---

## 2. 虹光项目现状与目标

### 2.1 当前架构特点

- **技术栈**：Spring Boot `2.3.7.RELEASE`、Spring Cloud Hoxton、Nacos 配置中心
- **数据库**：多微服务共用 MySQL 库 `hongguang`（同一 Schema）
- **数据源**：各服务通过 Nacos 共享配置 `druid-common.yaml` 获取连接信息，本地 `bootstrap.yaml` 不重复写 datasource
- **试点模块**：`hongguang-scheduling`（排产），历史表名 `schedule_flyway_history`

### 2.2 推广目标

```
┌─────────────────────────────────────────────────────────────┐
│                    MySQL 数据库: hongguang                   │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ scheduling   │ storage      │ parameter    │ ... 其他模块    │
│ schedule_    │ storage_     │ parameter_   │ {module}_      │
│ flyway_      │ flyway_      │ flyway_      │ flyway_history │
│ history      │ history      │ history      │                │
└──────────────┴──────────────┴──────────────┴────────────────┘
         ↑ 各模块独立历史表，避免版本记录互相污染
```

每个有数据库的微服务：

1. 引入 `flyway-core` 依赖
2. 在 `bootstrap.yaml` 配置 `spring.flyway.*`
3. 使用**独立的历史表名**（`{模块简写}_flyway_history`）
4. 新的 DDL/DML 变更只通过 `db/migration/` 新增脚本，不再手动执行 `db/` 下的零散 SQL

---

## 3. 技术栈与依赖说明

### 3.1 父 POM 已统一管理版本

`hongguang-parent/pom.xml`：

```xml
<properties>
    <flyway.version>6.4.4</flyway.version>
</properties>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.flywaydb</groupId>
            <artifactId>flyway-core</artifactId>
            <version>${flyway.version}</version>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### 3.2 子模块引入依赖

```xml
<!-- Flyway 数据库版本管理 -->
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-core</artifactId>
</dependency>
```

### 3.3 ⚠️ 虹光项目专用：不要用 spring-boot-starter-flyway


| 依赖                           | Spring Boot 2.3     | Spring Boot 3.0+ |
| ---------------------------- | ------------------- | ---------------- |
| `flyway-core`                | ✅ 推荐，由自动配置启用        | ✅ 可用             |
| `spring-boot-starter-flyway` | ❌ **不存在于 BOM，构建报错** | ✅ 官方 Starter     |


虹光项目基于 **Spring Boot 2.3.x**，classpath 上有 `flyway-core` 即可，Spring Boot 会自动装配 `FlywayAutoConfiguration`，**无需**也**不能**引入 `spring-boot-starter-flyway`。

---

## 4. 完整配置流程（新模块接入）

以 `hongguang-{module}` 为例，按以下 6 步操作。

### 步骤 1：确认模块需要 Flyway

满足以下条件的模块才接入：

- 是 Spring Boot 可执行服务（有 `main` 方法、打 jar 部署）
- 连接 MySQL 并持有本模块相关的表
- **不需要接入**：`hongguang-gateway`（网关）、`hongguang-job`（纯调度，无库）等

### 步骤 2：添加 Maven 依赖

在模块 `pom.xml` 的 `<dependencies>` 中加入 `flyway-core`（见 3.2）。

### 步骤 3：创建迁移脚本目录

```
hongguang-{module}/src/main/resources/
└── db/
    └── migration/          ← Flyway 只扫描此目录
        └── V1.0.0__init_xxx.sql
```

> `db/` 下其他历史脚本（如 `storage_ddl.sql`）**不会**被 Flyway 自动执行，仅作归档参考。

### 步骤 4：配置 bootstrap.yaml

配置必须写在 `spring.flyway` 下（不是 `springboot`），见 [第 8 节踩坑](#81-配置写在了错误的-yaml-前缀下)。

```yaml
spring:
  application:
    name: hongguang-{module}
  flyway:
    enabled: true
    baseline-on-migrate: true    # 已有数据的库首次接入时必须开启
    baseline-version: 0          # 必须为 0，见 8.2 节
    locations: classpath:db/migration
    encoding: UTF-8
    validate-on-migrate: true
    table: {module}_flyway_history   # 每模块独立历史表
```

**历史表命名建议：**


| 模块   | `spring.application.name` | 建议 `table` 值                    |
| ---- | ------------------------- | ------------------------------- |
| 排产   | hongguang-scheduling      | `schedule_flyway_history`       |
| 仓储   | hongguang-storage         | `storage_flyway_history`        |
| 参数   | hongguang-parameter       | `parameter_flyway_history`      |
| 质量   | hongguang-quality         | `quality_flyway_history`        |
| 物流   | hongguang-logistics       | `logistics_flyway_history`      |
| 设备   | hongguang-equipment       | `equipment_flyway_history`      |
| 表单   | hongguang-form            | `form_flyway_history`           |
| 生产作业 | hongguang-prod-operation  | `prod_operation_flyway_history` |
| 认证   | hongguang-auth-server     | `auth_flyway_history`           |
| 工作流  | hongguang-activiti        | `activiti_flyway_history`       |


---

## 5. SQL 脚本命名规范

Flyway 对文件名**极其严格**，格式错误会导致脚本被**静默忽略**。

### 5.1 版本化脚本（最常用）

```
V{版本号}__{描述}.sql
```


| 规则   | 说明                            |
| ---- | ----------------------------- |
| `V`  | 必须**大写** V                    |
| 版本号  | 数字或点分数字，如 `1`、`1.0.0`、`1.0.1` |
| `__` | 版本号后必须**两个下划线**               |
| 描述   | 英文下划线连接，**不能有空格**             |
| 后缀   | 必须是 `.sql`                    |


**正确示例：**


| 文件名                                   | 执行顺序  |
| ------------------------------------- | ----- |
| `V1.0.0__init_scheduling_tables.sql`  | 第 1 个 |
| `V1.0.1__add_remark_comment.sql`      | 第 2 个 |
| `V1.1.0__create_smelt_feed_batch.sql` | 第 3 个 |


**错误示例（会被忽略）：**


| 文件名                   | 错误原因          |
| --------------------- | ------------- |
| `v1__test.sql`        | 小写 v          |
| `V1_test.sql`         | 单下划线          |
| `V1__test script.sql` | 含空格           |
| `storage_ddl.sql`     | 不符合 Flyway 命名 |
| `smelt_feed_mvp.sql`  | 历史手工脚本命名      |


### 5.2 可重复执行脚本（慎用）

```
R__{描述}.sql
```

每次 checksum 变化时重新执行，适用于视图、存储过程刷新。虹光项目初期**建议只用 V 脚本**。

### 5.3 虹光项目版本号建议

- 新模块首个脚本：`V1.0.0__xxx.sql`
- 后续递增：`V1.0.1`、`V1.0.2` … 或 `V1.1.0`（小版本修 bug，中版本新功能）
- **避免**使用 `V1__xxx.sql`（与 baseline 默认版本 `1` 冲突，见 8.2 节）

---

## 6. 执行逻辑与历史表机制

### 6.1 空库首次启动

```
启动服务
  → Flyway 发现历史表不存在 → 自动创建 {module}_flyway_history
  → 表中无记录 → 依次执行 V1.0.0, V1.0.1, ...
  → 每执行完一条，写入 SUCCESS 记录
```

### 6.2 已有库再次启动（增量）

```
启动服务
  → 读取历史表已有版本
  → 对比 classpath 下脚本列表
  → 已记录的版本 → 跳过
  → 未记录的更高版本 → 执行
```

**结论：Flyway 是增量机制，不会重复执行已成功跑过的脚本。**

### 6.3 历史表字段说明

以排产模块为例（`schedule_flyway_history`）：


| 字段             | 含义    | 示例                                  |
| -------------- | ----- | ----------------------------------- |
| installed_rank | 执行序号  | 1, 2, 3                             |
| version        | 脚本版本  | `0`（baseline）、`1.0.0`               |
| description    | 脚本描述  | `update remark comment`             |
| type           | 类型    | `BASELINE` / `SQL`                  |
| script         | 脚本名   | `V1.0.0__update_remark_comment.sql` |
| checksum       | 内容校验和 | 用于检测已执行脚本是否被篡改                      |
| success        | 是否成功  | 1=成功                                |


---

## 7. 已有数据库接入（Baseline）

虹光各模块的数据库**早已有数据**，不是空库。首次接入 Flyway 必须使用 **Baseline** 机制。

### 7.1 配置

```yaml
spring:
  flyway:
    baseline-on-migrate: true   # 发现非空库且无历史表时，自动 baseline
    baseline-version: 0       # 将现有库标记为「版本 0」，后续 V1.0.0 才会执行
```

### 7.2 执行过程

```
非空库 hongguang + 无 schedule_flyway_history 表
  → baseline-on-migrate 触发
  → 创建 schedule_flyway_history
  → 插入一条 BASELINE 记录（version = 0）
  → 执行所有 version > 0 的 migration（如 V1.0.0）
```

### 7.3 期望的历史表数据

接入成功且 `V1.0.0` 已执行后：


| installed_rank | version | type     | description           |
| -------------- | ------- | -------- | --------------------- |
| 1              | 0       | BASELINE | << Flyway Baseline >> |
| 2              | 1.0.0   | SQL      | update remark comment |


### 7.4 首次接入踩坑后的修复（已 baseline 但 migration 未执行）

若历史表只有一条 `version=1` 的 BASELINE（未设 `baseline-version: 0` 时的旧行为）：

```sql
-- 清空错误的历史记录
DELETE FROM schedule_flyway_history;
```

修正 `bootstrap.yaml` 中 `baseline-version: 0` 后重新部署，Flyway 会重新 baseline 并执行待跑脚本。

---

## 8. 虹光项目踩坑记录（必读）

本节记录 `hongguang-scheduling` 试点中的真实问题，**推广到其他模块前务必通读**。

### 8.1 配置写在了错误的 YAML 前缀下

**现象：**

```
FlywayException: Found non-empty schema(s) `hongguang` but no schema history table.
Use baseline() or set baselineOnMigrate to true ...
```

**原因：** `flyway` 和 `jpa` 被放在了 `springboot:` 下，而 Spring Boot 只识别 `spring.flyway.`*。

```yaml
# ❌ 错误 — Flyway 读不到，baseline-on-migrate 不生效
springboot:
  flyway:
    baseline-on-migrate: true

# ✅ 正确
spring:
  flyway:
    baseline-on-migrate: true
```

**排查：** 看配置是否生效，启动日志中 Flyway 是否打印 `baselineOnMigrate: true`。`springboot:` 在本项目中**仅用于 license 配置**。

---

### 8.2 baseline 默认版本与 V1.0.0 冲突（migration 被跳过）

**现象：** 服务启动成功，历史表有 BASELINE 记录，但 migration SQL 未执行，表结构/注释无变化。

**历史表实际数据：**

```sql
-- 只有这一条，version = '1'
INSERT INTO schedule_flyway_history (..., version, type, ...)
VALUES (..., '1', 'BASELINE', ...);
```

**原因：**


| 配置项                  | 默认值        | 实际效果                             |
| -------------------- | ---------- | -------------------------------- |
| `baseline-version`   | `1`        | 将现有库标记为「已在版本 1」                  |
| 脚本 `V1.0.0__xxx.sql` | 版本 `1.0.0` | Flyway 认为 `1.0.0` ≤ `1`，**跳过执行** |


**修复：**

```yaml
spring:
  flyway:
    baseline-version: 0   # 必须显式设为 0
```

**规则：** 首个 migration 从 `V1.0.0` 开始时，`baseline-version` **必须为 `0`**。若首个脚本是 `V2.0.0`，则 `baseline-version` 可设为 `1` 或 `1.9.9`，但必须**低于**首个 migration 版本。

---

### 8.3 使用了 spring-boot-starter-flyway（构建失败）

**现象：**

```
'dependencies.dependency.version' for org.springframework.boot:spring-boot-starter-flyway:jar is missing.
```

**原因：** `spring-boot-starter-flyway` 是 Spring Boot 3.0 才有的 Starter，2.3 的 BOM 中不存在。

**修复：** 只保留 `flyway-core`，删除 `spring-boot-starter-flyway`。

---

### 8.4 多服务共用库但历史表未隔离

**风险：** 若多个模块都用默认表名 `flyway_schema_history`，在同一 Schema 下会互相覆盖执行记录，导致版本混乱。

**修复：** 每个模块配置独立的 `table`：

```yaml
spring:
  flyway:
    table: storage_flyway_history    # 仓储模块
    table: schedule_flyway_history   # 排产模块
```

---

### 8.5 Nacos 远程配置覆盖本地 Flyway 配置

**风险：** `bootstrap.yaml` 中 Flyway 配对了，但 Nacos 上 `{spring.application.name}.yaml` 里有冲突项（如 `spring.flyway.enabled: false`），远程配置优先级更高。

**排查：**

1. 登录 Nacos 控制台 → 命名空间 `hongguang` → 分组 `HONGGUANG_GROUP`
2. 检查 `hongguang-{module}.yaml` 是否含 `spring.flyway` 相关配置
3. 建议 Flyway 配置**统一写在本地 `bootstrap.yaml`**，Nacos 中不重复配置

---

## 9. 绝对禁止的操作


| 禁止行为                  | 后果                            | 正确做法                            |
| --------------------- | ----------------------------- | ------------------------------- |
| 修改已执行的 migration 脚本内容 | Flyway 校验 checksum 失败，或静默忽略修改 | 新建 `V1.0.1__fix_xxx.sql` 修正     |
| 删除已执行的脚本文件            | 新环境缺表/缺字段，启动失败                | 永久保留历史脚本                        |
| 随意 DELETE/UPDATE 历史表  | 状态机损坏，重复执行或校验失败               | 仅在明确排障时按文档操作                    |
| 生产环境开启 `flyway.clean` | **删除所有表和数据**                  | 生产必须 `clean-disabled: true`（默认） |
| 脚本中使用 `NOW()` 等动态值    | checksum 不稳定                  | SQL 保持静态确定性                     |
| 多环境共用同一历史表            | 版本记录互相污染                      | 每环境独立库，或独立历史表                   |


---

## 10. 配置模板速查

### 10.1 模块 pom.xml 片段

```xml
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-core</artifactId>
</dependency>
```

### 10.2 bootstrap.yaml 标准模板

```yaml
spring:
  application:
    name: hongguang-{module}
  jpa:
    hibernate:
      ddl-auto: validate          # 接入 Flyway 后推荐
    properties:
      hibernate:
        dialect: org.hibernate.dialect.MySQL57InnoDBDialect
  flyway:
    enabled: true
    baseline-on-migrate: true
    baseline-version: 0
    locations: classpath:db/migration
    encoding: UTF-8
    validate-on-migrate: true
    table: {module}_flyway_history

springboot:
  license:
    verify:
      # license 配置保持不变，不要放在 springboot 下的 flyway/jpa
      ...
```

### 10.3 migration 脚本模板

```sql
-- 修改 {table} 表的 {column} 字段
-- 版本: V1.0.1
-- 描述: {简要说明}
-- 模块: hongguang-{module}
-- 作者: {name}
-- 日期: {yyyy-MM-dd}

ALTER TABLE {table}
  MODIFY COLUMN {column} VARCHAR(255) COMMENT '{新注释}';
```

---

*文档版本：v1.0 | 更新日期：2026-06-22 | 基于 hongguang-scheduling 试点经验编写*