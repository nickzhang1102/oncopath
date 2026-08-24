# 贡献指南

感谢你对 OncoPath 的关注！欢迎以任何形式参与贡献：提交问题、修复 Bug、完善功能、改进文档。

## 贡献流程

1. **Fork** 本仓库到你的 GitHub 账号。
2. **克隆**你的 fork 到本地：
   ```bash
   git clone https://github.com/<你的用户名>/oncopath.git
   cd oncopath
   ```
3. **关联上游**以便同步最新变更：
   ```bash
   git remote add upstream https://github.com/nickzhang1102/oncopath.git
   git fetch upstream
   ```
4. **创建分支**，从最新的 `main` 切出：
   ```bash
   git checkout -b feature/your-feature      # 新功能
   # 或
   git checkout -b fix/your-bugfix           # Bug 修复
   # 或
   git checkout -b refactor/your-refactor    # 重构
   ```
5. **开发与自测**，遵循下文代码规范，并为新增功能补充测试。
6. **提交**，遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：
   ```bash
   git commit -m "feat(consultation): 完善 AgentTeams 会诊历史展示"
   git commit -m "fix(ocr): 修复检验类报告指标去重逻辑"
   git commit -m "refactor(patient): 抽取 PHI 加密为统一工具"
   ```
   常用前缀：`feat` / `fix` / `refactor` / `perf` / `docs` / `test` / `chore` / `style`。
7. **推送**到你的 fork：
   ```bash
   git push origin feature/your-feature
   ```
8. **发起 Pull Request**，目标分支为 `main`。在 PR 描述中说明：改了什么、为什么改、如何自测。若 PR 涉及行为变更，请附上测试。

## 代码规范

### Python（后端）

- 遵循 **PEP 8**。
- **必须使用类型提示**（type hints）。
- 文档字符串使用 **Google Style**。
- **全面使用 async/await**，异步 DB 会话与异步 HTTP 客户端。
- 数据验证使用 **Pydantic v2**。
- LLM 返回的 JSON 解析统一使用 `app/utils/llm_parser.py`，不要在各服务中手写 JSON 解析。
- 新增路由必须在 `app/routers.py` 注册，并补充对应的 schema 与（如有需要）模型。
- **安全要求**：
  - PHI 字段必须经 `EncryptionService` 加密后存储，禁止明文落库。
  - 禁止在代码中硬编码任何密钥、密码、API Key，一律走环境变量 / `config.py`。
  - 涉及明文 PHI 的接口必须记录审计日志。
  - SQL 查询使用 SQLAlchemy ORM，禁止字符串拼接 SQL。

### JavaScript（前端）

- 使用 **Vue 3 Composition API**（`<script setup>`）。
- 组件命名 **PascalCase**，变量与函数 **camelCase**。
- 状态管理使用 **Pinia**，新增 store 放在 `src/stores/`。
- API 调用统一封装在 `src/api/` 下，不要在组件中直接写 axios。
- 会诊执行能力通过 AgentTeams 集成实现，不要恢复已删除的本地 Leader/SSE 执行链。
- 图表使用 `src/utils/echarts.js` 按需导入，不要全量引入 ECharts。
- 颜色与样式使用 `src/styles/` 下的统一主题，不要散落硬编码色值。
- **安全要求**：
  - 任何 `v-html` 渲染前必须经过 `src/utils/sanitize.js`（DOMPurify）消毒。
  - 不在前端硬编码密钥或 Token。
  - 权限校验以后端为准，前端只做交互层控制。

### 通用

- 提交前请确保本地测试通过（见下文）。
- 不要在 PR 中夹带与本次改动无关的重构或格式化（保持 diff 聚焦）。
- 涉及数据库结构变更时，更新 Alembic public baseline（首次公开发布前）或新增迁移（公开发布后）；`back/scripts/init_fresh_db.py` 只维护幂等种子数据。

## 测试要求

- 新增功能或修复 Bug 时，**请补充对应的 pytest 测试**，放在 `back/tests/` 下。
- 测试命名：`test_<被测对象>.py`，函数命名 `test_<行为>`。
- 运行测试：
  ```bash
  cd back
  python -m venv .venv
  source .venv/bin/activate    # Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  pytest tests/ -v
  pytest tests/ -v -k "not integration"   # 仅单元测试
  ```

  > 也可使用 conda 等你熟悉的虚拟环境方案，只需确保 Python 3.11+ 且依赖安装完整。

## 提交 Issue

- Bug 报告请描述：复现步骤、期望行为、实际行为、环境（Python/Node 版本、是否 Docker 部署）。
- 功能建议请说明：使用场景、期望的交互方式。

## 行为准则

请保持友善与专业，尊重每一位贡献者。对医疗数据相关的讨论请特别注意隐私保护，不要在 Issue / PR / 评论中粘贴真实的患者信息或凭据。

---

再次感谢你的贡献！
