# AgentTeams 集成部署说明

本文说明 OncoPath 如何接入外部 AgentTeams 项目来执行虚拟会诊。OncoPath 只负责患者资料整理、会诊 prompt、启动代理、历史壳和 iframe 展示；会诊执行、额度、扣费和使用记录由 AgentTeams 的 OncoPath 集成服务账户负责。启动请求会先落到 OncoPath 的持久化 launch intent，再由 `agentteams-launch-worker` 派发或查询状态：超时/断连返回 `202` 并进入确认态，后续只查询状态，不重复发送 launch，也不会重复扣费；超过有限重试窗口后进入人工复核。

## 前置条件

- OncoPath 已部署并可通过 HTTPS 访问。
- AgentTeams 已部署，且启用了 OncoPath 集成 API。
- AgentTeams 内已有 OncoPath 集成服务账户，普通登录禁用，额度充足。
- 已生成一组只用于 OncoPath 集成的 `integration_secret`。

不要把真实 `integration_secret` 提交到 Git、截图、日志或工单中。

## OncoPath 后台配置

以管理员登录 OncoPath，进入后台的 AgentTeams 配置页，填写：

| 字段 | 示例 | 说明 |
|---|---|---|
| AgentTeams 地址 | `/agentteams` | 推荐同站反代路径；也可填写完整 HTTPS URL |
| 是否启用 | `启用` | 关闭时用户只看到配置提示，不会创建会诊 |
| 集成密钥 | `change-me-in-agentteams-too` | 必须与 AgentTeams 侧配置一致；保存后只显示掩码 |
| 提示标题/说明 | `需要配置 AgentTeams 项目` | 未配置或关闭时展示给普通用户 |
| CTA 文案/链接 | `了解部署方案` / `https://example.com/agentteams` | 可选；为空时不显示外链按钮 |

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

使用仓库自带 `docker-compose.yml` 时，frontend nginx 已内置 `/agentteams/` 反代，默认转发到宿主机 `8080` 端口；backend 容器通过 `AGENTTEAMS_INTERNAL_ORIGIN` 访问这个同站反代入口，默认值为 `http://frontend`。如果 AgentTeams 不在宿主机 `8080`，需要同步调整 `front/nginx.conf` 的 `/agentteams/` upstream，或改用一个 backend 容器可直接访问的完整 HTTPS URL。

Compose 启动时只有 `backend` 执行 Alembic 迁移和种子初始化；`agentteams-launch-worker` 依赖 backend 健康检查后启动，并设置 `RUN_DB_MIGRATIONS=false`。如果手工升级数据库，先停止 worker，确认 `/api/v1/health` 返回 200 后再启动 worker。

在启动结果仍未确认或已进入人工复核时，OncoPath 会阻止删除相关会诊记录或患者（返回 409），以免把可能已经扣费的远端会诊变成无主数据。已接受的会诊仍可按产品契约删除 OncoPath 本地壳；这不会删除 AgentTeams 远端会话，删除前应确认远端数据保留策略。

## 验证步骤

1. 在 OncoPath 后台保存 AgentTeams 配置并启用。
2. 用普通用户打开“虚拟会诊”。
3. 点击“开始会诊”。
4. 如果 AgentTeams 可用且额度充足，页面应进入 `/home/consultation/{conversation_id}` 并显示 AgentTeams iframe。
5. 回到会诊列表，点击历史记录，应再次打开 AgentTeams 会诊详情。

后端可用性 API 不返回密钥：

```bash
curl -H "Authorization: Bearer <token>" \
  https://oncopath.example.com/api/v1/consultation/agentteams/availability
```

响应里应包含 `configured`、`enabled`、`base_url`、`upsell`，不应包含 `integration_secret`。

## 常见错误

| 错误标题 | 常见原因 | 处理方式 |
|---|---|---|
| 需要配置 AgentTeams 项目 | OncoPath 未保存配置、未启用，或 AgentTeams 地址/密钥为空 | 在 OncoPath 后台补齐配置并启用 |
| AgentTeams 服务账户未配置 | AgentTeams 侧没有 OncoPath 集成服务账户 | 在 AgentTeams 管理后台完成服务账户配置 |
| 会诊额度已用完 | AgentTeams OncoPath 服务账户余额不足 | 为 AgentTeams OncoPath 服务账户增加会诊额度 |
| AgentTeams 集成未启用 | AgentTeams 侧关闭了 OncoPath 集成 | 在 AgentTeams 管理后台启用集成 |
| AgentTeams 版本不兼容 | AgentTeams 版本不支持 OncoPath launch/renew API | 升级 AgentTeams |
| AgentTeams 集成密钥无效 | OncoPath 和 AgentTeams 两侧密钥不一致 | 重新生成并同步 `integration_secret` |
| AgentTeams 暂时不可用 | AgentTeams 服务不可达、反代错误或返回格式异常 | 检查 AgentTeams 进程、Nginx 反代和服务日志 |

错误弹窗不会展示原始异常、内部 URL、traceback 或密钥。定位问题时请查看服务端日志，不要把真实患者资料或密钥贴到公开渠道。

## 安全边界

- OncoPath 不保存 AgentTeams 源码，也不包含 AgentTeams 私有部署授权逻辑。
- OncoPath 不对虚拟会诊扣费；次数边界由 AgentTeams 服务账户负责。
- iframe 使用短期 embed token，只应访问单条 AgentTeams 会话。
- AgentTeams 分享不在当前能力内；不要把 OncoPath 本地 `share_token` 当作 AgentTeams embed token 使用。
- 本项目仅用于健康信息整理和辅助理解，不替代医生诊断或治疗建议。
