# Docker 部署指南

医疗报告系统 v2.0 —— 基于 Docker Compose 的完整部署文档。

## 目录

- [环境要求](#环境要求)
- [选择 PaddleOCR CPU 或 GPU 环境](#选择-paddleocr-cpu-或-gpu-环境)
- [快速部署（首次）](#快速部署首次)
- [详细步骤](#详细步骤)
- [数据库迁移](#数据库迁移)
- [日常运维](#日常运维)
- [更新部署](#更新部署)
- [数据备份与恢复](#数据备份与恢复)
- [安全加固](#安全加固)
- [故障排查](#故障排查)

---

## 环境要求

### 硬件配置

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 存储 | 20 GB | 50 GB SSD |

GPU 部署另需 NVIDIA GPU（建议 8 GB 或以上显存）、支持 CUDA 12.6 的驱动和 NVIDIA Container Toolkit。完整前提与验证见 [PaddleOCR CPU / NVIDIA GPU 部署指南](./ocr-cpu-gpu.md)。

> 后端服务含 PaddleOCR 和 LLM 模型缓存，首次启动会下载约 2-3 GB 模型文件。

### 软件要求

| 软件 | 最低版本 | 检查命令 |
|------|---------|---------|
| Docker | 20.10+ | `docker --version` |
| Docker Compose | 2.0+ | `docker compose version` |
| Git | 任意 | `git --version` |

## 选择 PaddleOCR CPU 或 GPU 环境

- **CPU 是默认环境**：仅使用 `docker-compose.yml`，适合没有 NVIDIA GPU 的机器。
- **GPU 是独立覆盖环境**：始终同时使用 `docker-compose.yml` 和 `docker-compose.gpu.yml`，安装 PaddlePaddle 3.2.0 CUDA 12.6 wheel，并使用 `gpu:0`。
- 两种环境不能通过重启热切换；切换必须重建 backend。详细构建、验证、切换和排障命令见 [PaddleOCR CPU / NVIDIA GPU 部署指南](./ocr-cpu-gpu.md)。

### 网络要求（国内环境）

| 资源 | 地址 | 用途 |
|------|------|------|
| Docker Hub / 镜像源 | 需配置国内镜像 | 拉取基础镜像 |
| registry.npmmirror.com | 443 | 前端 npm 依赖（已配置） |
| pypi.tuna.tsinghua.edu.cn | 443 | Python 依赖（已配置） |
| hf-mirror.com | 443 | HuggingFace 模型（已配置） |
| www.paddlepaddle.org.cn | 443 | PaddlePaddle 安装（已配置） |
| cdn.playwright.dev | 443 | Playwright Chromium 官方下载源 |

> Dockerfile 中已配置 Python/npm 国内镜像源。仍需确保 Docker Hub 和 Playwright 官方浏览器下载源可达（拉取 `node:22-alpine`、`redis:7-alpine`、`pgvector/pgvector:pg17`、`nginx:alpine` 等基础镜像和 Chromium）。

---

## 快速部署（首次）

```bash
# 1. 克隆项目
git clone <repository-url>
cd oncopath

# 2. 生成密钥并创建 .env
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
cp .env.example .env
sed -i "s/your-super-secret-key-change-this-in-production-must-be-at-least-32-chars/${SECRET_KEY}/" .env
sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${ENCRYPTION_KEY}|" .env
# 手动编辑 .env，填写 DB_PASSWORD、REDIS_PASSWORD、LLM_API_KEY 等

# 3. 构建并启动（默认 CPU 环境）
docker compose -p oncopath up -d --build

# 4. backend entrypoint 自动执行 Alembic 迁移和幂等种子初始化

# 5. 验证
curl http://localhost:3000          # 前端页面
curl http://localhost:3000/api/v1/health   # 通过前端反代检查后端
```

> ⚠️ backend entrypoint 会先执行 `alembic upgrade head`，再运行 `init_fresh_db.py` 创建默认管理员（admin）、医疗标准指标库和指标分类。默认管理员密码为 `admin123`，首次登录后请立即修改。可通过环境变量 `ADMIN_INITIAL_PASSWORD` 自定义。

---

## 详细步骤

### 第 1 步：克隆项目

```bash
git clone <repository-url>
cd oncopath
```

### 第 2 步：配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，**以下为必填项**：

```bash
# ============ 必须修改 ============

# 数据库密码（强密码）
DB_PASSWORD=YourStr0ngDBPassword!

# Redis 密码（强密码）
REDIS_PASSWORD=YourStr0ngRedisPassword!

# JWT 签名密钥（至少 32 字符，用以下命令生成）
# openssl rand -hex 32
SECRET_KEY=<粘贴生成的密钥>

# PHI 加密密钥（Fernet 格式，用以下命令生成）
# python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=<粘贴生成的密钥>

# ============ 按需配置 ============

# LLM API（本地 AI 解读与知识库摘要使用）
LLM_API_KEY=your-llm-api-key
LLM_API_BASE=http://host.docker.internal:3456   # 宿主机 LLM 服务
LLM_MODEL_NAME=glm-5

# OCR 专用 LLM（图片报告 OCR 依赖）
OCR_LLM_API_KEY=your-ocr-api-key
OCR_LLM_API_BASE=https://api.openai.com/v1
OCR_LLM_MODEL_NAME=gpt-4o

# CORS（填前端实际访问地址，多个用逗号分隔）
CORS_ORIGINS=["http://your-domain.com","http://your-domain.com:3000"]

# 前端端口（宿主机映射）
FRONTEND_PORT=3000

# 指标解读专用 LLM（留空则回退到 LLM_*）
INTERPRETATION_LLM_API_KEY=
INTERPRETATION_LLM_API_BASE=
INTERPRETATION_LLM_MODEL_NAME=
```

> **安全提示**：`ENCRYPTION_KEY` 一旦设定并加密了数据，**不可更改**，否则已加密的患者数据将无法解密。请妥善备份此密钥。

### 第 3 步：构建并启动

```bash
# 构建镜像（首次约 10-20 分钟，取决于网络）
docker compose -p oncopath up -d --build

# 查看构建进度
docker compose -p oncopath logs -f backend
```

> 首次构建会下载 PaddleOCR 模型（约 2 GB），后续构建会利用 Docker 缓存。NVIDIA GPU 部署不要直接使用本命令，应按 [GPU 部署步骤](./ocr-cpu-gpu.md#nvidia-gpu-环境) 同时叠加 `docker-compose.gpu.yml`。

### 第 4 步：检查服务状态

```bash
# 查看所有容器状态
docker compose -p oncopath ps

# 期望输出（全部 healthy / running）：
# NAME                STATUS
# oncopath-postgres   running (healthy)
# oncopath-redis      running
# oncopath-backend    running
# oncopath-frontend   running
```

如果 backend 容器反复重启，查看日志排查：
```bash
docker compose -p oncopath logs backend --tail=50
```

### 第 5 步：初始化数据库

backend entrypoint 在每次启动时按固定顺序执行：
1. `alembic upgrade head` 创建或升级 schema，并记录 Alembic revision
2. `init_fresh_db.py` 幂等创建默认管理员账号（admin / admin123）
3. 幂等初始化指标分类（36 种分类）
4. 幂等初始化医疗标准指标库（血常规 / 生化 / 肿瘤标志物 / 凝血 / 尿常规，共 65 项）

自定义管理员密码：
```bash
docker compose -p oncopath exec -e ADMIN_INITIAL_PASSWORD=YourAdminPassword backend python scripts/init_fresh_db.py
```

### 第 6 步：访问系统

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端页面 | `http://<服务器IP>:3000` | 移动端适配 |
| API 健康检查 | `http://<服务器IP>:3000/api/v1/health` | 通过前端反代访问 |

---

## 数据库迁移

### 场景一：全新数据库（推荐）

启动 backend 容器即可自动完成，见[第 5 步](#第-5-步初始化数据库)。手工执行时必须先运行 `alembic upgrade head`，再运行 `python scripts/init_fresh_db.py`。

### 场景二：公开版本升级

从已发布的公开版本升级时，按仓库内连续的 Alembic revision 执行迁移：

```bash
# 查看当前迁移版本
docker compose -p oncopath exec backend alembic current

# 查看待执行的迁移
docker compose -p oncopath exec backend alembic history

# 执行所有待迁移
docker compose -p oncopath exec backend alembic upgrade head

# 回滚一个版本（谨慎使用）
docker compose -p oncopath exec backend alembic downgrade -1
```

### 场景三：生成新迁移（开发环境）

当模型变更后需要创建新的迁移文件：

```bash
# 自动生成迁移（对比模型与数据库差异）
docker compose -p oncopath exec backend alembic revision --autogenerate -m "描述变更内容"

# 检查生成的迁移文件
# 文件位于 back/migrations/versions/

# 执行迁移
docker compose -p oncopath exec backend alembic upgrade head
```

### 场景四：导入已有 PostgreSQL 备份

如需将已有 PostgreSQL 数据导入当前部署，可先导出再导入：

```bash
# 1. 在旧数据库上导出
pg_dump -h <旧数据库地址> -U postgres -d medical_report --no-owner --no-acl -f backup.sql

# 2. 启动新的容器化部署
docker compose -p oncopath up -d

# 3. 等待 PostgreSQL 就绪后导入
docker compose -p oncopath exec -T postgres psql -U postgres -d medical_report < backup.sql

# 4. 检查 Alembic 迁移状态
docker compose -p oncopath exec backend alembic current
```

> 备份来源必须与某个公开 Alembic revision 对应。版本不匹配时不要直接 `stamp`，应先恢复与该备份匹配的应用版本，再按公开迁移链升级。

### 迁移文件清单

首次公开版本包含一个压平后的迁移起点；后续 schema 变更在其上追加增量 revision：

| 版本 | 说明 |
|------|------|
| public_schema_baseline | 首次公开版本的完整 schema 基线 |
| 后续增量迁移 | 模型、约束或数据变更，每项单独追加 revision |

---

## 日常运维

### 查看日志

```bash
# 所有服务
docker compose -p oncopath logs -f

# 单个服务
docker compose -p oncopath logs -f backend
docker compose -p oncopath logs -f frontend
docker compose -p oncopath logs -f postgres

# 最近 100 行
docker compose -p oncopath logs --tail=100 backend
```

### 重启服务

```bash
# 重启所有
docker compose -p oncopath restart

# 重启单个服务
docker compose -p oncopath restart backend

# 重建并重启（代码变更后）
docker compose -p oncopath up -d --build backend
```

### 查看资源占用

```bash
# 容器资源使用
docker stats oncopath-postgres oncopath-redis oncopath-backend oncopath-frontend

# 磁盘占用
docker system df
```

### 进入容器调试

```bash
# 进入后端容器
docker compose -p oncopath exec backend bash

# 进入数据库
docker compose -p oncopath exec postgres psql -U postgres -d medical_report

# 进入 Redis
docker compose -p oncopath exec redis redis-cli -a <REDIS_PASSWORD>
```

---

## 更新部署

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重建镜像并重启（数据库迁移会自动通过 Alembic 执行，如果配置了的话）
docker compose -p oncopath up -d --build

# 3. 手动执行数据库迁移（如有新迁移文件）
docker compose -p oncopath exec backend alembic upgrade head

# 4. 验证
curl http://localhost:3000/api/v1/health
```

> 如果更新涉及模型变更，务必在步骤 3 执行迁移。

---

## 数据备份与恢复

### 手动备份

```bash
# 同时备份 PostgreSQL 和 app_storage，默认写入 ./backups
bash scripts/backup.sh
```

### 恢复数据

```bash
# 停止后端（避免写入冲突）
docker compose -p oncopath stop backend

# 在空数据库上恢复 custom-format dump。先按实际备份文件名修改路径。
cat backups/medical_database_YYYYMMDD_HHMMSS.dump | \
  docker compose -p oncopath exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl'

# 恢复文件存储前先备份当前卷；以下命令会覆盖同名文件。
docker compose -p oncopath run --rm --no-deps \
  -v "$(pwd)/backups:/backup:ro" --entrypoint sh backend \
  -c 'tar -xzf /backup/medical_storage_YYYYMMDD_HHMMSS.tar.gz -C /app/storage'

# 重启后端
docker compose -p oncopath start backend
```

### 定时备份（crontab）

```bash
# 在宿主机上添加定时任务
crontab -e

# 每天凌晨 2 点备份数据库和文件存储
0 2 * * * cd /path/to/oncopath && BACKUP_DIR=/data/backups bash scripts/backup.sh >> /var/log/oncopath-backup.log 2>&1
```

### Docker Volume 说明

| Volume | 内容 | 重要性 |
|--------|------|--------|
| `oncopath_postgres_data` | PostgreSQL 数据 | 🔴 关键 — 丢失=数据全无 |
| `oncopath_redis_data` | Redis 持久化（AOF） | 🟡 可重建 — 会话/缓存 |
| `oncopath_app_storage` | 上传的文件/图片 | 🔴 关键 — 用户上传数据 |
| `oncopath_huggingface_cache` | HF 模型缓存 | 🟢 可重建 — 自动下载 |
| `oncopath_paddlex_models` | PaddleX 模型 | 🟢 可重建 — 自动下载 |
| `oncopath_paddleocr_models` | PaddleOCR 模型 | 🟢 可重建 — 自动下载 |

---

## 安全加固

### 1. 密钥管理

```bash
# 生成 SECRET_KEY
openssl rand -hex 32

# 生成 ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

- `ENCRYPTION_KEY` 一旦用于加密数据，**不可更改**
- 备份 `ENCRYPTION_KEY` 到安全位置（密码管理器 / KMS）
- 生产环境禁止使用 `ALLOW_UNENCRYPTED_PHI=true`

### 2. 密码策略

| 项目 | 要求 |
|------|------|
| DB_PASSWORD | 至少 12 位，含大小写+数字+特殊字符 |
| REDIS_PASSWORD | 至少 16 位随机字符串 |
| SECRET_KEY | 至少 32 位（`openssl rand -hex 32` 生成 64 位） |
| ADMIN_INITIAL_PASSWORD | 首次部署时设置，部署后立即修改 admin 密码 |

### 3. 网络隔离

当前配置中 PostgreSQL、Redis 和后端 API 端口**不暴露到宿主机**，仅通过 Docker 内部网络 `medical-network` 访问。前端默认只绑定 `127.0.0.1:3000`，由宿主机反向代理提供公网 HTTPS。

### 4. 端口暴露

| 端口 | 服务 | 建议 |
|------|------|------|
| 3000 | 前端 | 生产环境通过 Nginx 反代 + HTTPS |
| 8000 | 后端 API | 仅 Docker 内部网络，通过前端 Nginx 代理 |
| 5432 | PostgreSQL | 不暴露（内部网络） |
| 6379 | Redis | 不暴露（内部网络） |

### 5. HTTPS 配置

在宿主机上安装 Nginx + Let's Encrypt，反代到前端 3000 端口：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. Docker 容器安全

当前 Dockerfile 已配置：
- ✅ 非 root 用户运行（`appuser`，通过 gosu 切换）
- ✅ 最小化基础镜像（`python:3.11-slim`）
- ✅ 资源限制（CPU / Memory）
- ✅ 只读挂载（`.claude/agents:ro`）

---

## 故障排查

### 后端容器反复重启

```bash
# 查看日志
docker compose -p oncopath logs backend --tail=50

# 常见原因：
# 1. SECRET_KEY 使用了默认值 → 修改 .env
# 2. ENCRYPTION_KEY 格式错误 → 重新生成
# 3. PostgreSQL 未就绪 → 等待 healthcheck 通过
# 4. DB_PASSWORD/REDIS_PASSWORD 未设置 → .env 中填写
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 状态
docker compose -p oncopath ps postgres

# 测试连接
docker compose -p oncopath exec postgres psql -U postgres -d medical_report -c "SELECT 1;"

# 检查密码是否匹配
docker compose -p oncopath exec backend env | grep DB_PASSWORD
```

### 前端白页 / API 404

```bash
# 检查后端是否正常
curl http://localhost:3000/api/v1/health

# 检查 CORS 配置
docker compose -p oncopath exec backend env | grep CORS_ORIGINS

# 检查 Nginx 代理日志
docker compose -p oncopath logs frontend
```

### OCR 功能不工作

先确认部署选择的是 CPU 还是 GPU；GPU 环境的 wheel、容器权限与设备检查见 [PaddleOCR CPU / NVIDIA GPU 部署指南](./ocr-cpu-gpu.md#故障排查)。

```bash
# 检查模型是否下载成功
docker compose -p oncopath exec backend ls -la /app/.paddleocr/
docker compose -p oncopath exec backend ls -la /app/.paddlex/

# 检查 OCR LLM 配置
docker compose -p oncopath exec backend env | grep OCR_LLM

# 手动测试 PaddleOCR
docker compose -p oncopath exec backend python -c "from paddleocr import PaddleOCR; print('OK')"
```

### AgentTeams 会诊入口不工作

```bash
# 检查 OncoPath 后端日志中的 AgentTeams 集成错误
docker compose -p oncopath logs backend --tail=100 | grep -i agentteams

# 检查前端 Nginx 的 /agentteams/ 反向代理
docker compose -p oncopath exec frontend nginx -T | grep -A8 'location /agentteams/'
```

确认 OncoPath 管理后台已保存并启用 AgentTeams 配置，且两侧 `integration_secret` 一致。完整排查步骤见 [AgentTeams 集成部署说明](./agentteams-integration.md)。会诊执行和额度由外部 AgentTeams 服务负责，不使用 OncoPath 的本地 LLM、计费或 Celery 队列。

### 磁盘空间不足

```bash
# 查看 Docker 磁盘占用
docker system df

# 清理无用镜像
docker image prune -a

# 清理构建缓存
docker builder prune

# ⚠️ 不要使用 docker volume prune — 会删除数据
```

### 完全重置

```bash
# ⚠️ 危险操作：删除所有数据
docker compose -p oncopath down -v
docker compose -p oncopath up -d --build
```

---

## 服务架构

```
                    ┌─────────────┐
                    │   用户浏览器  │
                    └──────┬──────┘
                           │ :3000
                    ┌──────▼──────┐
                    │   Frontend   │  nginx:alpine
                    │  (Nginx SPA) │  静态文件 + API 代理
                    └──────┬──────┘
                           │ 内部代理 /api → :8000
                    ┌──────▼──────┐
                    │   Backend    │  python:3.11-slim
                    │  (FastAPI)   │  REST + 通知/上传 SSE
                    └──┬────┬──┬──┘
                       │    │  │
              ┌────────┘    │  └────────┐
              │             │           │
       ┌──────▼──────┐ ┌───▼────┐ ┌────▼─────┐
       │  PostgreSQL  │ │ Redis  │ │ LLM API  │
       │  (pgvector)  │ │ (缓存) │ │ (宿主机) │
       │  :5432 内部  │ │ :6379  │ │ :3456    │
       └─────────────┘ └────────┘ └──────────┘
```

---

## 环境变量速查表

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DB_PASSWORD` | ✅ | — | PostgreSQL 密码 |
| `REDIS_PASSWORD` | ✅ | — | Redis 密码 |
| `SECRET_KEY` | ✅ | — | JWT 签名密钥 (≥32字符) |
| `ENCRYPTION_KEY` | ✅ | — | Fernet 加密密钥 |
| `DB_USER` | ❌ | postgres | 数据库用户 |
| `DB_NAME` | ❌ | medical_report | 数据库名 |
| `LLM_API_KEY` | ❌ | — | 本地 AI 解读与知识库摘要 LLM 密钥 |
| `LLM_API_BASE` | ❌ | host.docker.internal:3456 | 本地 AI 解读与知识库摘要 LLM 地址 |
| `LLM_MODEL_NAME` | ❌ | glm-5 | 本地 AI 解读与知识库摘要 LLM 模型 |
| `OCR_LLM_API_KEY` | ❌ | — | OCR LLM 密钥 |
| `OCR_LLM_API_BASE` | ❌ | api.openai.com/v1 | OCR LLM 地址 |
| `OCR_LLM_MODEL_NAME` | ❌ | gpt-4o | OCR LLM 模型 |
| `INTERPRETATION_LLM_*` | ❌ | 回退到 LLM_* | 解读专用 LLM |
| `CORS_ORIGINS` | ❌ | localhost | 前端访问地址 |
| `FRONTEND_PORT` | ❌ | 3000 | 前端映射端口 |
| `STORAGE_TYPE` | ❌ | local | 存储类型 |
| `STORAGE_PATH` | ❌ | /app/storage | 存储路径 |
| `ALLOW_UNENCRYPTED_PHI` | ❌ | false | 允许明文 PHI |
| `DEBUG` | ❌ | false | 调试模式 |
