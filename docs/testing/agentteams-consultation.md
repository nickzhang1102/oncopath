# AgentTeams 会诊集成测试说明

本文说明 OncoPath 侧如何验证 AgentTeams 会诊集成。测试只使用占位配置、mock 响应和本地 fixture；不要在测试命令、截图或日志里写入真实 `integration_secret`、真实 AgentTeams 地址或真实患者资料。

## 覆盖矩阵

| 场景 | 测试文件 | 覆盖点 |
|---|---|---|
| 后台配置 API | `back/tests/test_agentteams_config_api.py` | 配置保存、掩码返回、availability 不泄露密钥 |
| start/embed/history | `back/tests/test_agentteams_start_embed.py` | 启动 AgentTeams 会诊、embed 映射、历史详情、旧本地入口下线 |
| 启动恢复与删除保护 | `back/tests/test_agentteams_start_embed.py` | 断连后只查询不重发、退避/人工复核、未确认启动阻止会诊/患者删除 |
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

## 边界

- 本测试文档不新增运行时能力。
- OncoPath 不模拟 AgentTeams 分享能力，也不把本地 `share_token` 当作 AgentTeams embed token。
- OncoPath 不处理 AgentTeams 私有部署授权；会诊次数和扣费边界由 AgentTeams 服务账户负责。
- 本项目只用于健康信息整理、辅助理解和分析，不替代医生诊断或治疗建议。
