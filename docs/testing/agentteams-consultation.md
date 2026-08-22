# AgentTeams 会诊集成测试说明

本文说明 OncoPath 侧如何验证 AgentTeams 会诊集成。测试只使用占位配置、mock 响应和本地 fixture；不要在测试命令、截图或日志里写入真实 `integration_secret`、真实 AgentTeams 地址或真实患者资料。

## 覆盖矩阵

| 场景 | 测试文件 | 覆盖点 |
|---|---|---|
| 后台配置 API | `back/tests/test_agentteams_config_api.py` | 配置保存、掩码返回、availability 不泄露密钥 |
| start/embed/history | `back/tests/test_agentteams_start_embed.py` | 启动 AgentTeams 会诊、embed 映射、历史详情、旧本地入口下线 |
| 启动恢复与删除保护 | `back/tests/test_agentteams_start_embed.py` | 断连后只查询不重发、退避/人工复核、未确认启动阻止会诊/患者删除 |
| 人工复核与审计 | `back/tests/test_agentteams_start_embed.py` | admin-only 权限、只读对账不重发、confirmed-not-created 解锁、并发 lease、重复处置和审计理由 |
| PHI 快照生命周期 | `back/tests/test_agentteams_start_embed.py` | accepted/rejected 立即清理 payload、manual_review 保留快照、迁移 head 和终态回读 |
| 后端错误映射 | `back/tests/test_agentteams_start_embed.py` | quota、service account、integration disabled、unsupported version、invalid integration key、unknown raw body fallback |
| upsell 和 start 错误 UX | `front/tests/e2e/agentteams-upsell.spec.js` | 未配置提示、开始会诊、容量和配置类错误弹窗 |
| iframe 和历史详情 | `front/tests/e2e/agentteams-embed.spec.js` | 桌面/移动 iframe 展示、历史记录、详情失败提示 |

## 后端验证

在 PowerShell 中运行：

```powershell
cd back
$env:PYTHONPATH='.'; @'
import sys, types, pytest
paddleocr = types.ModuleType('paddleocr')
class PaddleOCR:
    def __init__(self, *args, **kwargs): pass
    def ocr(self, *args, **kwargs): return []
paddleocr.PaddleOCR = PaddleOCR
sys.modules['paddleocr'] = paddleocr
sys.modules['paddle'] = types.ModuleType('paddle')
sys.modules['cv2'] = types.ModuleType('cv2')
raise SystemExit(pytest.main([
    'tests/test_agentteams_config_api.py',
    'tests/test_agentteams_start_embed.py',
    '-q',
]))
'@ | python -
```

这里显式 stub `paddleocr`、`paddle` 和 `cv2`，避免本地没有 OCR 运行库时影响 AgentTeams 集成测试。

## 前端验证

在 PowerShell 中运行：

```powershell
cd front
npm run build
npx playwright test tests/e2e/agentteams-embed.spec.js tests/e2e/agentteams-upsell.spec.js --reporter=line
```

Playwright 配置通常会自动启动前端测试服务。若本地配置没有启用 `webServer`，先启动前端开发服务，再运行同一条 Playwright 命令。

## 失败场景核对

| 失败场景 | 期望表现 |
|---|---|
| OncoPath 未配置或未启用 AgentTeams | 普通用户看到“需要配置 AgentTeams 项目”，不会创建本地会诊 |
| AgentTeams 服务账户缺失 | 弹窗标题为“AgentTeams 服务账户未配置” |
| AgentTeams 额度不足 | 弹窗标题为“会诊额度已用完” |
| AgentTeams 侧集成关闭 | 弹窗标题为“AgentTeams 集成未启用” |
| AgentTeams 版本不支持 | 弹窗标题为“AgentTeams 版本不兼容” |
| `integration_secret` 不一致 | 弹窗标题为“AgentTeams 集成密钥无效” |
| AgentTeams 不可达或返回未知错误 | 只展示“AgentTeams 暂时不可用”，不泄露原始异常 |
| 旧本地 Leader/SSE 记录 | 不恢复本地会诊，只返回不可用或无本地会话提示 |
| iframe 桌面/移动视口 | iframe 在宽屏和窄屏下都保持可见、可滚动、无遮挡 |

## 人工复核与 PHI 验收边界

- `GET /api/v1/admin/agentteams-launch-intents?status=manual_review` 和详情接口只能由 admin 调用；响应可包含 request ID、患者/账户引用、错误摘要、payload hash 和 `payload_retained`，不得包含 `payload_ciphertext`、完整 prompt 或 integration secret。
- `POST /api/v1/admin/agentteams-launch-intents/{id}/reconcile` 只查询 AgentTeams 已有 request ID；找到远端记录后补写映射并记录 `read_only_reconcile` 审计，必须证明 launch POST 次数没有增加，人工复核绝不重发 launch POST。
- `POST /api/v1/admin/agentteams-launch-intents/{id}/resolve` 仅接受 `confirmed_not_created`，要求至少 10 个非空白字符的外部核验理由；该动作将旧 intent 置为 `rejected`、清理终态 payload 并解除旧锁，不创建下一场会诊。
- 数据库抽样只查询状态、计数和清理时间，不查询 ciphertext 内容。目标 PostgreSQL 应执行类似：

```sql
select status,
       count(*) as intents,
       count(payload_ciphertext) as retained_payloads,
       count(payload_purged_at) as purged_payloads
from agentteams_launch_intents
group by status
order by status;
```

- 预期状态矩阵：`prepared/dispatching/confirming/manual_review` 可以保留快照；`accepted/rejected` 不应有 ciphertext 且应有 `payload_purged_at`。备份和副本也必须按同一规则抽样，禁止把完整 prompt 写入日志或验收附件。
- OncoPath 本地清理不等于删除 AgentTeams 远端会诊；远端保留/删除按 AgentTeams 侧策略执行，演练记录只保存 request ID、状态和审计摘要。

## 边界

- 本测试文档不新增运行时能力。
- OncoPath 不模拟 AgentTeams 分享能力，也不把本地 `share_token` 当作 AgentTeams embed token。
- OncoPath 不处理 AgentTeams 私有部署授权；会诊次数和扣费边界由 AgentTeams 服务账户负责。
- 本项目只用于健康信息整理、辅助理解和分析，不替代医生诊断或治疗建议。
