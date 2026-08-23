# 🧬 OncoPath

**把散落各处的医疗报告，整理成一条看得懂的治疗之路**

检验指标 OCR 自动识别 · 治疗时间线聚合 · AI 辅助解读 · 多智能体虚拟会诊入口

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-早期公开版-yellow.svg)](#状态说明)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)](#快速开始docker)
[![Frontend](https://img.shields.io/badge/frontend-Vue%203-42b883.svg)](#快速开始docker)
[![Docker](https://img.shields.io/badge/deploy-Docker%20Compose-2496ED.svg?logo=docker&logoColor=white)](#快速开始docker)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-181717.svg?logo=github)](https://nickzhang1102.github.io/oncopath/)

**[简体中文](./README.md)** | [English](./README.en.md)

![OncoPath 首页指标图表](docs/screenshots/desktop-home-indicators-chart.png)

[项目网站](https://nickzhang1102.github.io/oncopath/) · [快速开始](#-快速开始docker) · [界面预览](#-界面预览) · [参与贡献](#-参与贡献) · [☕ 请作者喝咖啡](#-赞助支持)

> **状态说明**：本项目已公开，当前处于早期版本阶段。欢迎试用与反馈；生产环境部署前必须完成本文档【安全说明】中的全部必改项，并自行评估当地医疗数据合规要求。

---

## 🎯 为什么做 OncoPath

肿瘤治疗是一场以年计的持久战。作为患者家属，你大概率遇到过这些问题：

| 现实困境 | OncoPath 的回答 |
|---------|----------------|
| 📋 检验报告一摞摞，指标和参考值看不懂 | 手机拍照上传，**OCR 自动识别 + LLM 匹配标准指标库**，专业指标翻译成通俗语言 |
| 📁 报告散落在微信、纸质袋、各家医院系统里 | 检验 / 检查 / 病理 / 用药 / 随访**五源聚合成一条治疗时间线**，可追溯、可筛选、可导出 PDF |
| 📉 关键指标的变化趋势只能靠手抄对比 | 异常指标自动追踪，任意指标**趋势图表 + 组合横向对比** |
| 🏥 见医生前想不好该问什么 | 一键聚合病历资料生成会诊提示词，通过 **AgentTeams 集成发起多智能体虚拟会诊** |

OncoPath 面向懂技术的患者家属和家庭自部署场景：数据存在你自己的服务器上，敏感字段全程加密，AI 只做信息整理与辅助理解——最终判断永远属于你和医生。

---

## ✨ 核心功能

### 📊 数据采集与理解
| 功能 | 说明 |
|------|------|
| 🔍 **OCR 指标提取** | PaddleOCR 识别 → LLM 解析表格 → LLM 匹配标准库自动落库；检验类 / 检查类 / 病理类三种处理流程自动分流；识别结果支持人工审查修正 |
| 📷 **图片报告管理** | 27 种报告分类、上传去重校验、SSE 实时处理进度、缩略图时间线 |
| 🤖 **AI 检验解读** | 整体评估 + 异常指标解读 + 趋势变化 + 建议提醒；自动从解读中提取复查建议并创建随访提醒 |

### 🗂️ 全景健康档案
| 功能 | 说明 |
|------|------|
| 🧑‍⚕️ **患者管理** | 多患者支持；姓名 / 电话 / 身份证 Fernet 加密存储 + 单向哈希索引查重；PHI 编辑审计日志 |
| 📈 **治疗时间线** | 5 张表统一聚合，里程碑标记、多维筛选、日期范围统计 |
| 💊 **用药与打卡** | 用药记录 CRUD（含停药）、服药打卡（taken/skipped/missed）、依从性统计（7–365 天） |
| ⏰ **随访提醒** | 手动 / AI 解读 / 会诊三种来源，pending → sent → confirmed 闭环 |
| 🧪 **组合指标查询** | 多项相关指标按日期对齐横向比较，一键切入趋势图 |
| 🔎 **全局搜索** | 跨检验 / 检查 / 病理 / 用药 / 时间线模糊搜索 |

### 🤝 会诊与知识沉淀
| 功能 | 说明 |
|------|------|
| 🏛️ **虚拟会诊（AgentTeams）** | 聚合病历资料生成会诊提示词，外部 AgentTeams 项目执行多智能体会诊，iframe 内嵌展示，历史与会话分享完整保留 |
| 📚 **知识库** | 分类树、文档上传下载预览搜索、访问日志，支持 txt/pdf/office/图片 |
| 📤 **导出与分享** | 检验报告 / 时间线 / 完整病历 PDF 导出（内置中文字体）；ShareToken 限时限次分享 |

### ⚙️ 平台支撑
| 功能 | 说明 |
|------|------|
| 📱 **响应式双端** | Vant 4 移动端优先，桌面端自适应布局 |
| 🛡️ **仪表盘** | 当前用药 / 异常指标 / 待审 OCR / 进行中会诊 / 待办随访一站式总览 |
| 👨‍💼 **管理后台** | 用户管理、指标标准库 CRUD / 拖拽排序 / 批量导入、指标分类管理 |
| 🔐 **安全体系** | JWT + SSO 单点登录、登录失败锁定（Redis Lua）、SlowAPI 限流、DOMPurify XSS 防护、路径遍历防护 |

---

## 📸 界面预览

> 以下截图均由当前前端以固定的虚构演示数据自动生成。姓名、联系方式、证件号等身份字段已掩码，并带有"演示数据 · 已脱敏"标记；不含真实患者资料。生成与审查规则见 [截图维护说明](docs/screenshots/README.md)。

**首页重要指标** — 报告数量、异常项、待办与分组指标一个工作台搞定

![首页重要指标列表](docs/screenshots/desktop-home-indicators-list.png)

**检验报告详情** — 原始指标、异常状态、参考范围与 AI 解读同页呈现

![检验报告详情](docs/screenshots/desktop-lab-report.png)

### 📁 更多截图（检查 / 病理 / 组合指标 / 会诊 / 知识库 / 移动端）

**检查报告** — 检查所见、诊断意见与随访提示统一呈现

![检查报告](docs/screenshots/desktop-exam-report.png)

**病理报告** — 病理诊断、组织学、免疫组化与基因检测按结构归集

![病理报告](docs/screenshots/desktop-pathology-report.png)

**组合指标表格** — 多项指标按日期对齐，便于横向比较

![组合指标表格](docs/screenshots/desktop-indicator-comparison-table.png)

**组合指标趋势** — 选择一到两项指标直接进入趋势图

![组合指标趋势](docs/screenshots/desktop-indicator-comparison-chart.png)

**虚拟会诊工作台** — 聚合资料并承接 AgentTeams 多智能体会诊过程

![虚拟会诊工作台](docs/screenshots/desktop-consultation-room.png)

**知识库** — 分类、搜索、摘要与预览沉淀随访护理资料

![知识库](docs/screenshots/desktop-knowledge-base.png)

**移动端**

| ![移动端首页](docs/screenshots/mobile-home.png) | ![移动端检验报告](docs/screenshots/mobile-lab-report.png) | ![移动端组合指标](docs/screenshots/mobile-indicator-comparison.png) | ![移动端虚拟会诊](docs/screenshots/mobile-consultation.png) | ![移动端知识库](docs/screenshots/mobile-knowledge-base.png) |
|---|---|---|---|---|

---

## 🚀 快速开始（Docker）

最快的方式是用 Docker Compose 一键拉起完整环境。

### 1️⃣ 克隆与配置

```bash
git clone https://github.com/nickzhang1102/oncopath.git
cd oncopath
cp .env.example .env
```

编辑 `.env`，**必须填写**以下 4 项（其余按需调整）：

| 变量 | 说明 | 生成方式 |
|------|------|----------|
| `SECRET_KEY` | JWT 签名密钥，至少 32 字符，启动时校验拒绝默认值 | `openssl rand -hex 32` |
| `DB_PASSWORD` | PostgreSQL 密码 | 自定义强密码 |
| `REDIS_PASSWORD` | Redis 密码 | 自定义强密码 |
| `ENCRYPTION_KEY` | PHI 字段 Fernet 加密密钥（生产必填） | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

> **LLM 配置无需预填**：AI 解读、OCR 解析等 AI 功能使用的 OpenAI 兼容 LLM 配置，部署完成后登录系统，按首启引导进入「个人中心 → AI 配置」菜单填写并测试即可（配置加密存库、保存后热生效）。`.env` 中的 `LLM_*` 变量仅作为可选回退。AgentTeams 使用独立的后台集成配置，详见 [`docs/deployment/agentteams-integration.md`](./docs/deployment/agentteams-integration.md)。

### 2️⃣ 启动服务

```bash
docker compose up -d
docker compose ps
```

容器端口映射（与 `docker-compose.yml` 一致）：
- **前端**：默认仅绑定宿主机 `127.0.0.1:3000` → 容器 `80`（Nginx）
- **后端 API / PostgreSQL / Redis**：仅通过 Docker 内部网络访问，不发布宿主端口

如需局域网直接访问前端，可显式设置 `FRONTEND_BIND_ADDRESS=0.0.0.0`；生产环境建议保持 loopback，由宿主机反向代理提供 HTTPS。

### 3️⃣ 初始化数据库

backend 容器启动时会自动执行 `alembic upgrade head` 建立/升级表结构，再运行幂等种子脚本创建默认管理员、指标分类和标准指标。`agentteams-launch-worker` 等待 backend 健康后启动，不参与迁移。默认管理员账号为 `admin`，密码取自 `ADMIN_INITIAL_PASSWORD` 环境变量，未设置则使用默认密码 `admin123`（**生产环境务必设置 `ADMIN_INITIAL_PASSWORD` 并登录后立即修改**）。

### 4️⃣ 访问

- 前端：http://localhost:3000
- API 健康检查：http://localhost:3000/api/v1/health

---

## 🛳️ 生产部署

生产部署以 `docker-compose.yml` 为准。部署前请逐项确认【安全说明】中的必改项：

PaddleOCR 默认使用 CPU。NVIDIA GPU 环境需要同时叠加 `docker-compose.gpu.yml`，并预先安装 NVIDIA Container Toolkit；两套环境的硬件要求、完整命令、验证、切换和排障见 [PaddleOCR CPU / NVIDIA GPU 部署指南](./docs/deployment/ocr-cpu-gpu.md)。

- 修改 `.env` 中的 `SECRET_KEY`、`DB_PASSWORD`、`REDIS_PASSWORD`、`ENCRYPTION_KEY`
- 部署后登录系统，在「个人中心 → AI 配置」完成 LLM 配置（或在 `.env` 预填 `LLM_*` 回退值）
- 设置 `ADMIN_INITIAL_PASSWORD` 为强密码，并登录后立即修改 admin 密码
- `CORS_ORIGINS` 限制为实际前端域名
- `ALLOW_UNENCRYPTED_PHI` 保持 `false`（生产环境必须配置 `ENCRYPTION_KEY`）
- 配置 HTTPS（在 `docker-compose.yml` 的 frontend 段取消 443 端口注释并提供 SSL 证书，或由外部反向代理终结 TLS）
- 设置防火墙规则，仅开放 80/443
- 保持 `FRONTEND_BIND_ADDRESS=127.0.0.1`，由宿主机反向代理公开 80/443
- 配置 PostgreSQL 定时备份

```bash
# 生产启动
docker compose --env-file .env up -d

# backend entrypoint 会自动迁移 schema 并初始化幂等种子数据
```

---

## 🔒 安全说明

### 数据安全
- **PHI 字段加密**：患者姓名、电话、身份证等敏感字段使用 Fernet 对称加密静态存储；身份证号单向 SHA-256 哈希索引用于查重。
- **密码存储**：bcrypt 哈希。
- **PHI 访问审计**：患者编辑接口访问明文 PHI 时记录审计日志；列表/详情接口返回脱敏数据。

### 认证与授权
- **JWT + SSO 单点登录**：SessionService 基于 Redis 实现会话管理，新登录踢下线旧会话，旧 Token 进入黑名单。
- **登录失败锁定**：5 次 / 15 分钟，基于 Redis Lua 原子操作。
- **管理后台**：所有 `/api/v1/admin` 端点需 admin 角色鉴权。

### 接口与运行时安全
- **默认认证**：所有接口默认需要认证（除登录/注册/分享链接等）。
- **限流**：SlowAPI，登录 5/min、会诊 5/min、上传 10/min、默认 100/min。
- **SQL 注入防护**：SQLAlchemy ORM 参数化查询。
- **XSS 防护**：前端 v-html 渲染前使用 DOMPurify 消毒。
- **路径遍历防护**：StorageService 解析路径时校验，禁止越界访问。

### 生产环境必改项

| 项 | 说明 |
|----|------|
| `SECRET_KEY` | 使用 `openssl rand -hex 32` 生成强随机值，启动时校验拒绝默认值 |
| `DB_PASSWORD` / `REDIS_PASSWORD` | 使用强密码 |
| `ENCRYPTION_KEY` | 使用 `Fernet.generate_key()` 生成；**若库中已有用旧 key 加密的 PHI 数据，轮换时必须先用旧 key 解密再用新 key 重新加密** |
| `ADMIN_INITIAL_PASSWORD` | 设置强密码，登录后立即修改 |
| `CORS_ORIGINS` | 限制为实际前端域名，不要使用通配 |
| `ALLOW_UNENCRYPTED_PHI` | 保持 `false` |

---

## 🗺️ Roadmap

- [ ] 微信 OAuth 登录
- [ ] Token 迁移到 httpOnly cookie + CSRF 防护
- [ ] 知识库 PDF / Office 在线预览完善
- [ ] 前端单元测试与 E2E 测试补全
- [ ] 英文界面 i18n 支持

---

## ⚠️ 医疗免责声明

**本系统的 AgentTeams 虚拟会诊入口、检验指标解读、OCR 识别等功能仅作健康信息整理、辅助理解和辅助分析，不构成医疗诊断或治疗建议，也不属于医疗器械用途，不能替代执业医师的专业判断。** 本系统不适用于紧急医疗情况；使用者应自行核实系统输出并咨询合格执业医师。使用本系统造成的任何后果由使用者自行承担。详见 [DISCLAIMER.md](./DISCLAIMER.md)。

---

## 📄 License

本项目基于 [Apache License 2.0](./LICENSE) 开源。第三方依赖和镜像资产保留各自许可证，详见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。

版权所有 © 2026 nickzhang1102

---

## 🤝 参与贡献

欢迎参与贡献！请阅读 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解 Fork → 分支 → 提交 → PR 的完整流程与代码规范。

---

## ☕ 赞助支持

如果 OncoPath 对你有所帮助，欢迎请作者喝一杯咖啡 ☕

**每一份支持都是作者持续维护的动力，真的很重要！**

| 💚 微信 | 💙 支付宝 |
| :---: | :---: |
| ![微信赞赏码](docs/screenshots/wechat.jpg) | ![支付宝收款码](docs/screenshots/alipay.jpg) |

也欢迎点一个 ⭐ Star，让更多有需要的人看到这个项目。
