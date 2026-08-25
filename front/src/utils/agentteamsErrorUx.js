// AgentTeams 开源仓库地址（前端引导链接唯一来源，与后端 DEFAULT_UPSELL.cta_url 保持一致）
export const AGENTTEAMS_REPO_URL = 'https://github.com/nickzhang1102/agentTeams'

const ERROR_COPY = {
  agentteams_quota_exceeded: {
    title: 'AgentTeams 会诊服务不可用',
    message: '当前部署返回了旧版服务错误，请检查两端 AgentTeams 版本和集成配置。开源自部署不需要额外购买服务。',
    cta_label: '查看配置说明',
  },
  agentteams_service_account_not_configured: {
    title: 'AgentTeams 服务账户未配置',
    message: '当前 AgentTeams 尚未配置 OncoPath 集成账户，请在 AgentTeams 管理后台完成配置后继续使用虚拟会诊。',
    cta_label: '查看配置说明',
  },
  agentteams_integration_disabled: {
    title: 'AgentTeams 集成未启用',
    message: '当前部署已关闭 OncoPath 集成，请在 AgentTeams 管理后台启用后继续使用。',
    cta_label: '查看配置说明',
  },
  agentteams_unsupported_version: {
    title: 'AgentTeams 版本不兼容',
    message: '当前 AgentTeams 版本不支持 OncoPath 集成，请升级 AgentTeams 后继续使用虚拟会诊。',
    cta_label: '查看升级说明',
  },
  agentteams_not_configured: {
    title: '需要配置 AgentTeams 项目',
    message: '当前 OncoPath 尚未配置可用的 AgentTeams 项目，请完成部署和集成配置后继续使用虚拟会诊。',
    cta_label: '查看配置说明',
  },
  agentteams_invalid_integration_key: {
    title: 'AgentTeams 集成密钥无效',
    message: '当前 OncoPath 与 AgentTeams 的集成密钥不匹配，请检查两端配置后重试。',
    cta_label: '查看配置说明',
  },
  agentteams_unavailable: {
    title: 'AgentTeams 暂时不可用',
    message: '当前无法连接 AgentTeams 服务，请稍后重试，或检查 AgentTeams 服务和反向代理是否正常运行。',
    cta_label: '查看配置说明',
  },
  agentteams_idempotency_conflict: {
    title: '会诊启动标识已失效',
    message: '本次启动标识已用于其他会诊，请关闭提示后重新发起。',
    cta_label: '重新发起',
  },
  launch_failed: {
    title: '会诊启动失败',
    message: '当前未能启动 AgentTeams 会诊，请稍后重试；如果问题持续存在，请检查 AgentTeams 集成配置。',
    cta_label: '查看配置说明',
  },
}

function extractAgentTeamsErrorCode(errorOrCode) {
  if (!errorOrCode) return ''
  if (typeof errorOrCode === 'string') return errorOrCode
  const detail = errorOrCode.response?.data?.detail || errorOrCode.detail
  if (typeof detail === 'object' && detail?.error) return String(detail.error)
  return ''
}

export function getAgentTeamsErrorUx(errorOrCode, options = {}) {
  const code = extractAgentTeamsErrorCode(errorOrCode)
  const copy = ERROR_COPY[code] || {
    title: 'AgentTeams 会诊暂时不可用',
    message: '当前无法完成 AgentTeams 会诊操作，请稍后重试，或检查 AgentTeams 集成配置。',
    cta_label: '查看配置说明',
  }

  return {
    code,
    title: copy.title,
    message: copy.message,
    cta_label: copy.cta_label,
    cta_url: options.ctaUrl || '',
  }
}

export function isAgentTeamsError(errorOrCode) {
  const code = extractAgentTeamsErrorCode(errorOrCode)
  return Boolean(code && (ERROR_COPY[code] || code.startsWith('agentteams_')))
}
