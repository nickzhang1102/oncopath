import { test, expect } from '@playwright/test'

const baseURL = process.env.FRONT_BASE_URL || 'http://localhost:3000'

async function mockCommonApis(page, counters = {}) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'test-token')
    localStorage.setItem('refreshToken', 'test-refresh')
  })

  await page.route('**/api/v1/accounts/notifications/stream', route => {
    route.fulfill({ status: 204, body: '' })
  })
  await page.route('**/api/v1/accounts/notifications**', route => {
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) })
  })
  await page.route('**/api/v1/accounts/me', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        account_id: 1,
        username: 'testuser',
        account_name: '测试用户',
        account_type: 'user',
        status: 'active',
      }),
    })
  })
  await page.route('**/api/v1/consultation/conversations**', route => {
    if (route.request().method() === 'POST') {
      counters.createConversation = (counters.createConversation || 0) + 1
      route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({ id: 100, title: '虚拟会诊', status: 'new' }),
      })
      return
    }
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ conversations: [], total: 0, limit: 20, offset: 0 }),
    })
  })
  await page.route('**/api/v1/patients**', route => {
    counters.patients = (counters.patients || 0) + 1
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify([{ patient_id: 1, patient_name: '测试患者', is_primary: true }]),
    })
  })
}

test('shows AgentTeams upsell and does not start local consultation when unavailable', async ({ page }) => {
  const counters = {}
  await mockCommonApis(page, counters)

  await page.route('**/api/v1/consultation/agentteams/availability', route => {
    counters.availability = (counters.availability || 0) + 1
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        configured: false,
        enabled: false,
        base_url: '',
        capacity: null,
        upsell: {
          title: '需要配置 AgentTeams 项目',
          message: '部署 AgentTeams 后即可使用多 Agent 团队进行虚拟会诊分析。',
          demo_asset_url: 'https://example.com/demo.webp',
          cta_label: '了解部署方案',
          cta_url: 'https://example.com/agentteams',
        },
      }),
    })
  })

  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('button', { name: '开始会诊' }).first()).toBeVisible()
  const patientsBeforeClick = counters.patients || 0

  await page.getByRole('button', { name: '开始会诊' }).first().click()

  await expect(page.getByText('需要配置 AgentTeams 项目')).toBeVisible()
  await expect(page.getByRole('button', { name: '了解部署方案' })).toBeVisible()
  expect(counters.availability).toBe(1)
  expect(counters.patients || 0).toBe(patientsBeforeClick)
  expect(counters.createConversation || 0).toBe(0)
  await expect(page.getByText('https://example.com/agentteams')).toHaveCount(0)

  const popupPromise = page.waitForEvent('popup')
  await page.getByRole('button', { name: '了解部署方案' }).click()
  const popup = await popupPromise
  expect(popup.url()).toBe('https://example.com/agentteams')
})

test('starts AgentTeams flow when AgentTeams is enabled', async ({ page }) => {
  const counters = {}
  await mockCommonApis(page, counters)

  await page.route('**/api/v1/consultation/agentteams/availability', route => {
    counters.availability = (counters.availability || 0) + 1
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        configured: true,
        enabled: true,
        base_url: 'https://agentteams.example.com',
        capacity: null,
        upsell: { title: '', message: '', demo_asset_url: '', cta_label: '', cta_url: '' },
      }),
    })
  })
  await page.route('**/api/v1/consultation/agentteams/start', route => {
    counters.agentTeamsStart = (counters.agentTeamsStart || 0) + 1
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        conversation_id: 900,
        provider: 'agentteams',
        external_conversation_id: '1001',
        external_session_id: '2001',
        external_share_token: 'share-token',
        embed_url: '/agentteams/embed/conversation/embed-token',
        status: 'created',
      }),
    })
  })
  await page.route('**/api/v1/consultation/agentteams/sessions/900**', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        conversation_id: 900,
        provider: 'agentteams',
        external_conversation_id: '1001',
        external_session_id: '2001',
        external_share_token: 'share-token',
        embed_url: '/agentteams/embed/conversation/embed-token',
        status: 'created',
      }),
    })
  })
  await page.route('**/agentteams/embed/conversation/embed-token', route => {
    route.fulfill({
      contentType: 'text/html',
      body: '<html><body><main>AgentTeams embed</main></body></html>',
    })
  })

  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('button', { name: '开始会诊' }).first()).toBeVisible()

  await page.getByRole('button', { name: '开始会诊' }).first().click()

  await expect(page).toHaveURL(/\/home\/consultation\/900\?patient_id=1$/)
  await expect(page.locator('iframe.embed-iframe')).toBeVisible()
  await expect(page.getByText('需要配置 AgentTeams 项目')).toHaveCount(0)
  expect(counters.availability).toBe(1)
  expect(counters.agentTeamsStart).toBe(1)
  expect(counters.createConversation || 0).toBe(0)
})

const agentTeamsStartErrors = [
  { status: 502, error: 'agentteams_invalid_integration_key', title: 'AgentTeams 集成密钥无效' },
  { status: 402, error: 'agentteams_quota_exceeded', title: '会诊额度已用完' },
  { status: 403, error: 'agentteams_service_account_not_configured', title: 'AgentTeams 服务账户未配置' },
  { status: 403, error: 'agentteams_integration_disabled', title: 'AgentTeams 集成未启用' },
  { status: 426, error: 'agentteams_unsupported_version', title: 'AgentTeams 版本不兼容' },
  { status: 502, error: 'agentteams_unavailable', title: 'AgentTeams 暂时不可用' },
]

for (const scenario of agentTeamsStartErrors) {
  test(`shows productized AgentTeams start error: ${scenario.error}`, async ({ page }) => {
    const counters = {}
    await mockCommonApis(page, counters)

    await page.route('**/api/v1/consultation/agentteams/availability', route => {
      route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          configured: true,
          enabled: true,
          base_url: 'https://agentteams.example.com',
          capacity: null,
          upsell: {
            title: '',
            message: '',
            demo_asset_url: '',
            cta_label: '了解部署方案',
            cta_url: 'https://example.com/agentteams',
          },
        }),
      })
    })
    await page.route('**/api/v1/consultation/agentteams/start', route => {
      counters.agentTeamsStart = (counters.agentTeamsStart || 0) + 1
      route.fulfill({
        status: scenario.status,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: {
            error: scenario.error,
            message: 'raw internal http://agentteams.internal traceback secret',
          },
        }),
      })
    })

    await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })
    await page.getByRole('button', { name: '开始会诊' }).first().click()

    await expect(page.getByText(scenario.title)).toBeVisible()
    await expect(page.getByText('启动 AgentTeams 会诊失败，请稍后重试')).toHaveCount(0)
    await expect(page.getByText('agentteams.internal')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /增加额度|查看配置说明|查看升级说明/ })).toBeVisible()
    expect(counters.agentTeamsStart).toBe(1)
    expect(counters.createConversation || 0).toBe(0)
  })
}
