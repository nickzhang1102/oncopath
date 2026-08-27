# AgentTeams 集成部署说明

本文说明 OncoPath 如何接入开源 AgentTeams 项目来执行虚拟会诊。OncoPath 只负责患者资料整理、会诊 prompt、启动代理、历史壳和 iframe 展示；AgentTeams 负责模型、Agent、工具和会诊工作流。启动请求会先落到 OncoPath 的持久化 launch intent，再由 `agentteams-launch-worker` 派发或查询状态：超时/断连返回 `202` 并进入确认态，后续只查询状态，不重复发送 launch；超过有限重试窗口后进入人工复核。

## 前置条件

- OncoPath 已部署并可通过 HTTPS 访问。
- AgentTeams 已部署，且启用了 OncoPath 集成 API。
- AgentTeams 内已有 OncoPath 集成服务账户，普通登录禁用。该账户只用于会话归属和权限隔离，不承载计费或额度配置。
- 已生成一组只用于 OncoPath 集成的 `integration_secret`。

不要把真实 `integration_secret` 提交到 Git、截图、日志或工单中。

## OncoPath 后台配置

以管理员登录 OncoPath，进入后台的 AgentTeams 配置页，填写：

| 字段 | 示例 | 说明 |
|---|---|---|
| AgentTeams 地址 | `/agentteams` | 推荐同站反代路径；也可填写完整 HTTPS URL |
| 是否启用 | `启用` | 关闭时用户只看到配置提示，不会创建会诊 |
| 集成密钥 | `change-me-in-agentteams-too` | 必须与 AgentTeams 侧配置一致；保存后只显示掩码 |

推荐把 AgentTeams 地址配置为 `/agentteams`，让浏览器里的 iframe 与 OncoPath 同站，避免跨站 cookie、`SameSite` 和 CORS 问题。

## 推荐 Nginx 反向代理

下面示例假设：

- OncoPath 前端运行在 `127.0.0.1:3000`
- OncoPath 后端运行在 `127.0.0.1:8000`
- AgentTeams 运行在 `127.0.0.1:8080`
- 对外域名是 `oncopath.example.com`

```nginx
server {
    listen 443 ssl;
    server_name oncopath.example.com;

    ssl_certificate /etc/letsencrypt/live/oncopath.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/oncopath.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /agentteams/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
    }
}
```

配置完成后，OncoPath 后台的 AgentTeams 地址填写：

```text
/agentteams
```

使用仓库自带 `docker-compose.yml` 时，frontend nginx 已内置 AgentTeams 嵌入页、静态资源和集成 API 的受限反代，默认转发到宿主机 `8080` 端口；backend 容器通过 `AGENTTEAMS_INTERNAL_ORIGIN` 访问这个同站反代入口，默认值为 `http://frontend`。如果 AgentTeams 不在宿主机 `8080`，需要同步调整 `front/nginx.conf` 的 upstream，或改用一个 backend 容器可直接访问的完整 HTTPS URL。

Compose 启动时只有 `backend` 执行 Alembic 迁移和种子初始化；`agentteams-launch-worker` 依赖 backend 健康检查后启动，并设置 `RUN_DB_MIGRATIONS=false`。如果手工升级数据库，先停止 worker，确认 `/api/v1/health` 返回 200 后再启动 worker。

在启动结果仍未确认或已进入人工复核时，OncoPath 会阻止删除相关会诊记录或患者（返回 409），以免把可能仍在运行的远端会诊变成无主数据。已接受的会诊仍可按产品契约删除 OncoPath 本地壳；这不会删除 AgentTeams 远端会话，删除前应确认远端数据保留策略。

## launch worker 生产演练与升级顺序

以下命令应在目标环境或与生产配置等价的演练环境执行。演练记录只保留 request ID、状态、计数和错误摘要，不复制患者资料、prompt、密钥或完整响应体。

### 首启前置检查

```bash
# 检查 Compose 合并后的最终配置；确认 backend/worker 使用同一代码版本
docker compose -p oncopath config
docker compose -p oncopath build backend agentteams-launch-worker

# 先启动数据库、Redis 和 backend；worker 暂不启动
docker compose -p oncopath up -d postgres redis backend
docker compose -p oncopath ps
docker compose -p oncopath exec backend python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"

# backend healthy 后核对迁移 head，再启动 worker
docker compose -p oncopath exec backend alembic current
docker compose -p oncopath up -d agentteams-launch-worker
docker compose -p oncopath logs --tail=100 agentteams-launch-worker
```

预期：只有 backend 的环境包含 `RUN_DB_MIGRATIONS=true`；worker 包含 `RUN_DB_MIGRATIONS=false`，且日志没有执行迁移或 seed 的记录。迁移 head 必须为 `drop_prompt_config_system_prompt`。

### 崩溃恢复演练

每个场景都要在 AgentTeams 管理端或其只读审计接口核对同一 request ID 的远端 launch 状态和尝试次数。数据库只读检查示例：

```bash
docker compose -p oncopath exec -T postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "select request_id,status,attempt_count,remote_status from agentteams_launch_intents order by id desc limit 20;"'
```

1. **POST 前停止 worker**：确认未决 intent 在 worker 恢复后只派发一次。
2. **POST 已提交但响应丢失**：在远端已接受请求后停止 backend 或 worker，恢复服务，确认 OncoPath 继续使用原 request ID 并只做 status 查询；远端 launch 尝试次数应为 1。
3. **status 中断**：在对账等待期间重启 worker，确认 lease 过期后由新 worker 接管，迟到响应不能覆盖较新的状态。
4. **人工复核**：让 intent 进入 `manual_review`，分别演练“只读对账找到远端会诊”和“外部确认未创建”。前者只能补映射并收敛为 `accepted`，后者只能收敛为 `rejected` 并解除锁；两条路径都不得再次调用 launch POST。

每次演练至少保存：Compose config、容器状态、backend health 响应、迁移 head、worker 日志、request ID、远端 launch 状态、intent 前后状态和人工审计摘要。

### 人工复核与 PHI 快照检查

管理员只能在 `/admin` 的 AgentTeams 启动复核页操作 `manual_review` 记录。页面和 API 只展示 request ID、引用 ID、错误摘要、payload hash、保留状态和审计历史；不会解密或返回医疗 prompt、`payload_ciphertext` 或 integration secret。

只读对账使用 `POST /api/v1/admin/agentteams-launch-intents/{id}/reconcile`，只查询既有 request ID；确认远端存在后补写映射并接受。确认未创建使用 `.../{id}/resolve`，必须先在 AgentTeams 外部完成无创建核验并填写至少 10 个非空白字符的理由；该动作只拒绝旧 intent、清理终态快照和解除旧锁，不替用户发起下一次 launch。

目标 PostgreSQL 和备份副本验收时只做聚合抽样，不读取 ciphertext 内容：

```bash
docker compose -p oncopath exec -T postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "select status,count(*) as intents,count(payload_ciphertext) as retained_payloads,count(payload_purged_at) as purged_payloads from agentteams_launch_intents group by status order by status;"'
```

预期是未决状态可保留快照，`accepted/rejected` 的 `payload_ciphertext` 为空且 `payload_purged_at` 有值。备份、数据库副本和应用存储必须按部署方的保留策略管理；OncoPath 清理本地快照不会自动删除 AgentTeams 远端会诊内容。

### 升级与回滚边界

升级必须先停止旧 worker，再替换或迁移 backend；确认 backend healthy 和迁移 head 后，才启动新 worker，最后恢复 frontend。不要让旧 worker 在 schema 迁移期间继续轮询 launch intent。

```bash
docker compose -p oncopath stop agentteams-launch-worker
docker compose -p oncopath up -d --build backend
docker compose -p oncopath exec backend python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)"
docker compose -p oncopath exec backend alembic current
docker compose -p oncopath up -d agentteams-launch-worker frontend
```

回滚前必须保留数据库和 `/app/storage` 备份，并确认新版本没有写入旧版本无法理解的表或字段；不能只回退镜像后盲目执行 `alembic downgrade`。无法证明兼容时，保持 worker 停止，先恢复与备份匹配的应用版本，再按迁移链处理数据库。

## 验证步骤

1. 在 OncoPath 后台保存 AgentTeams 配置并启用。
2. 用普通用户打开“虚拟会诊”。
3. 点击“开始会诊”。
4. 如果 AgentTeams 可用且集成配置有效，页面应进入 `/home/consultation/{conversation_id}` 并显示 AgentTeams iframe。
5. 回到会诊列表，点击历史记录，应再次打开 AgentTeams 会诊详情。

后端可用性 API 不返回密钥：

```bash
curl -H "Authorization: Bearer <token>" \
  https://oncopath.example.com/api/v1/consultation/agentteams/availability
```

响应里应包含 `configured`、`enabled`、`base_url`、`upsell`，不应包含 `integration_secret`。`upsell` 仅为旧客户端兼容的只读提示；当前管理表单不再保存提示文案或额度信息。

## 常见错误

| 错误标题 | 常见原因 | 处理方式 |
|---|---|---|
| 需要配置 AgentTeams 项目 | OncoPath 未保存配置、未启用，或 AgentTeams 地址/密钥为空 | 在 OncoPath 后台补齐配置并启用 |
| AgentTeams 服务账户未配置 | AgentTeams 侧没有 OncoPath 集成服务账户 | 在 AgentTeams 管理后台完成服务账户配置 |
| AgentTeams 返回不兼容错误 | 连接到仍保留旧商业逻辑的 AgentTeams 版本 | 升级 AgentTeams，并检查两侧集成配置；当前开源版本不需要额外购买服务 |
| AgentTeams 集成未启用 | AgentTeams 侧关闭了 OncoPath 集成 | 在 AgentTeams 管理后台启用集成 |
| AgentTeams 版本不兼容 | AgentTeams 版本不支持通用 launch/status API | 升级 AgentTeams |
| AgentTeams 集成密钥无效 | OncoPath 和 AgentTeams 两侧密钥不一致 | 重新生成并同步 `integration_secret` |
| AgentTeams 暂时不可用 | AgentTeams 服务不可达、反代错误或返回格式异常 | 检查 AgentTeams 进程、Nginx 反代和服务日志 |

错误弹窗不会展示原始异常、内部 URL、traceback 或密钥。定位问题时请查看服务端日志，不要把真实患者资料或密钥贴到公开渠道。

## 安全边界

- OncoPath 不保存 AgentTeams 源码，也不包含 AgentTeams 私有部署授权逻辑。
- OncoPath 和当前开源 AgentTeams 都不对虚拟会诊计费；服务账户只用于会话归属和权限隔离。
- iframe 使用短期 embed token，只应访问单条 AgentTeams 会话。
- AgentTeams 分享不在当前能力内；不要把 OncoPath 本地 `share_token` 当作 AgentTeams embed token 使用。
- 本项目仅用于健康信息整理和辅助理解，不替代医生诊断或治疗建议。
