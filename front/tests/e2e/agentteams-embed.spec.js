import { test, expect } from '@playwright/test'

const baseURL = process.env.FRONT_BASE_URL || 'http://localhost:3000'

async function mockEmbedApis(page, counters = {}) {
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
  await page.route('**/api/v1/patients**', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify([{ patient_id: 1, patient_name: '测试患者', is_primary: true }]),
    })
  })
  await page.route('**/api/v1/consultation/conversations?**', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        conversations: [
          {
            id: 900,
            title: 'AgentTeams 历史会诊',
            patient_id: 1,
            share_token: 'local-share-token',
            provider: 'agentteams',
            external_session_status: 'created',
            status: 'analyzing',
            created_at: '2026-07-09T10:00:00',
            updated_at: '2026-07-09T10:00:00',
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      }),
    })
  })
  await page.route('**/api/v1/consultation/agentteams/sessions/900', route => {
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
      body: '<html><body style="margin:0"><main style="min-height:100vh">AgentTeams embed</main></body></html>',
    })
  })
}

async function expectIframeFitsViewport(page, minHeight) {
  const iframe = page.locator('iframe.embed-iframe')
  await expect(iframe).toBeVisible()
  const box = await iframe.boundingBox()
  const viewport = page.viewportSize()

  expect(box.width).toBeGreaterThan(300)
  expect(box.height).toBeGreaterThan(minHeight)
  expect(box.x).toBeGreaterThanOrEqual(0)
  expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 1)
  expect(box.y + box.height).toBeLessThanOrEqual(viewport.height + 1)
}

test('AgentTeams iframe fits desktop consultation detail', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 })
  await mockEmbedApis(page)

  await page.goto(`${baseURL}/home/consultation/900`, { waitUntil: 'domcontentloaded' })

  await expect(page.getByText('AgentTeams')).toBeVisible()
  await expectIframeFitsViewport(page, 600)
})

test('AgentTeams iframe fits mobile consultation detail', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await mockEmbedApis(page)

  await page.goto(`${baseURL}/home/consultation/900`, { waitUntil: 'domcontentloaded' })

  await expect(page.getByText('AgentTeams')).toBeVisible()
  await expectIframeFitsViewport(page, 620)
})

test('AgentTeams history item opens numeric detail even when share token exists', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 })
  const counters = {}
  await mockEmbedApis(page, counters)

  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })
  await page.getByText('AgentTeams 历史会诊').click()

  await expect(page).toHaveURL(/\/home\/consultation\/900$/)
  await expect(page.getByText('AgentTeams')).toBeVisible()
  await expect(page.locator('iframe.embed-iframe')).toHaveAttribute('src', '/agentteams/embed/conversation/embed-token')
})

test('legacy numeric detail without AgentTeams mapping shows error and does not request local session', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 })
  const counters = {}
  await mockEmbedApis(page, counters)
  await page.route('**/api/v1/consultation/agentteams/sessions/901', route => {
    counters.agentTeamsMissing = (counters.agentTeamsMissing || 0) + 1
    route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ detail: '外部会诊不存在' }),
    })
  })
  await page.route('**/api/v1/consultation/session/901', route => {
    counters.localSession = (counters.localSession || 0) + 1
    route.fulfill({
      status: 410,
      contentType: 'application/json',
      body: JSON.stringify({ detail: { error: 'local_consultation_disabled' } }),
    })
  })

  await page.goto(`${baseURL}/home/consultation/901`, { waitUntil: 'domcontentloaded' })

  await expect(page.getByText('此会诊记录不可用或已下线')).toBeVisible()
  await expect(page.getByText('Leader 消息')).toHaveCount(0)
  await expect(page.getByText('Agent 报告')).toHaveCount(0)
  await expect(page.getByText('最终报告')).toHaveCount(0)
  expect(counters.agentTeamsMissing).toBe(1)
  expect(counters.localSession || 0).toBe(0)
})

test('AgentTeams detail renew error uses productized copy without raw details', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 })
  await mockEmbedApis(page)
  await page.route('**/api/v1/consultation/agentteams/sessions/902', route => {
    route.fulfill({
      status: 426,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: {
          error: 'agentteams_unsupported_version',
          message: 'raw internal http://agentteams.internal traceback secret',
        },
      }),
    })
  })

  await page.goto(`${baseURL}/home/consultation/902`, { waitUntil: 'domcontentloaded' })

  await expect(page.getByText('AgentTeams 版本不兼容')).toBeVisible()
  await expect(page.getByText('当前 AgentTeams 版本不支持 OncoPath 集成，请升级 AgentTeams 后继续使用虚拟会诊。')).toBeVisible()
  await expect(page.getByText('agentteams.internal')).toHaveCount(0)

  await page.getByRole('button', { name: '查看处理方式' }).click()
  await expect(page.getByRole('button', { name: '查看升级说明' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'AgentTeams 版本不兼容' })).toBeVisible()
})
