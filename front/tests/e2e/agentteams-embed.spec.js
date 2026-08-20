import { test, expect } from '@playwright/test'

const baseURL = process.env.FRONT_BASE_URL || 'http://localhost:3000'

async function mockEmbedApis(page, counters = {}, options = {}) {
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
    counters.patientSwitches = route.request().method() === 'POST'
      ? [...(counters.patientSwitches || []), route.request().url()]
      : (counters.patientSwitches || [])
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify(options.patients || [
        { patient_id: 1, patient_name: '测试患者', is_primary: true },
      ]),
    })
  })
  await page.route('**/api/v1/consultation/conversations?**', async route => {
    counters.historyUrls = [...(counters.historyUrls || []), route.request().url()]
    const patientId = new URL(route.request().url()).searchParams.get('patient_id')
    const patientHistory = options.historyByPatient?.[patientId]
    if (patientHistory?.delay) {
      await new Promise(resolve => setTimeout(resolve, patientHistory.delay))
    }
    const suppliedConversations = options.conversationsByPatient?.[patientId]
    const conversations = suppliedConversations || (patientHistory
      ? [{
          id: patientHistory.id,
          title: patientHistory.title,
          patient_id: Number(patientId),
          provider: 'agentteams',
          external_session_status: 'completed',
          status: 'completed',
          created_at: '2026-07-09T10:00:00',
          updated_at: '2026-07-09T10:00:00',
        }]
      : [
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
        ])
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        conversations,
        total: conversations.length,
        limit: 20,
        offset: 0,
      }),
    })
  })
  await page.route('**/api/v1/consultation/agentteams/launch-intents/active?**', route => {
    counters.activeLaunchIntentCalls = (counters.activeLaunchIntentCalls || 0) + 1
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify(options.activeLaunchIntent || null),
    })
  })
  await page.route('**/api/v1/consultation/agentteams/sessions/900**', route => {
    counters.externalSessionCalls = (counters.externalSessionCalls || 0) + 1
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
  await page.route('**/api/v1/consultation/agentteams/sessions/900/status**', async route => {
    const payload = route.request().postDataJSON()
    counters.statusUpdates = [...(counters.statusUpdates || []), payload.status]
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        conversation_id: 900,
        provider: 'agentteams',
        external_conversation_id: '1001',
        external_session_id: '2001',
        embed_url: '/agentteams/embed/conversation/embed-token',
        status: options.statusResponseStatus || payload.status,
      }),
    })
  })
  await page.route('**/agentteams/embed/conversation/embed-token', route => {
    const embedStatuses = JSON.stringify(options.embedStatuses || ['completed'])
    route.fulfill({
      contentType: 'text/html',
      body: `<html><body style="margin:0"><main style="min-height:100vh">AgentTeams embed</main><script>
        const statuses = ${embedStatuses}
        statuses.forEach((status, index) => setTimeout(() => {
          window.parent.postMessage({ type: 'oncopath:embed-status', status, version: 'e2e-' + status }, window.location.origin)
          if (index === statuses.length - 1) document.body.dataset.statusSequenceDone = 'true'
        }, index * 25))
      </script></body></html>`,
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
  const counters = {}
  await mockEmbedApis(page, counters)

  await page.goto(`${baseURL}/home/consultation/900?patient_id=1`, { waitUntil: 'domcontentloaded' })

  await expect(page.getByText('AgentTeams')).toBeVisible()
  await expectIframeFitsViewport(page, 600)
  await expect(page.locator('.status-badge')).toContainText('已完成')
  await expect.poll(() => counters.statusUpdates || []).toContain('completed')
})

test('AgentTeams iframe fits mobile consultation detail', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await mockEmbedApis(page)

  await page.goto(`${baseURL}/home/consultation/900?patient_id=1`, { waitUntil: 'domcontentloaded' })

  await expect(page.getByText('AgentTeams')).toBeVisible()
  await expectIframeFitsViewport(page, 620)
  await expect(page.locator('.status-badge')).toContainText('已完成')
})

test('AgentTeams terminal status ignores a late running iframe update', async ({ page }) => {
  const counters = {}
  await mockEmbedApis(page, counters, { embedStatuses: ['completed', 'monitoring'] })

  await page.goto(`${baseURL}/home/consultation/900?patient_id=1`, { waitUntil: 'domcontentloaded' })

  const iframeBody = page.frameLocator('iframe.embed-iframe').locator('body')
  await expect(iframeBody).toHaveAttribute('data-status-sequence-done', 'true')
  await page.waitForTimeout(50)
  await expect(page.locator('.status-badge')).toContainText('已完成')
  expect(counters.statusUpdates).toEqual(['completed'])
})

test('AgentTeams status patch response is authoritative for the current badge', async ({ page }) => {
  const counters = {}
  await mockEmbedApis(page, counters, {
    embedStatuses: ['monitoring'],
    statusResponseStatus: 'completed',
  })

  await page.goto(`${baseURL}/home/consultation/900?patient_id=1`, { waitUntil: 'domcontentloaded' })

  await expect.poll(() => counters.statusUpdates || []).toContain('monitoring')
  await expect(page.locator('.status-badge')).toContainText('已完成')
})

test('AgentTeams history is scoped to the current patient and opens numeric detail', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1366, height: 768 })
  const counters = {}
  await mockEmbedApis(page, counters)

  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })
  await expect(page.getByText('测试患者').first()).toBeVisible()
  await expect.poll(() => counters.historyUrls.length).toBeGreaterThan(0)
  expect(new URL(counters.historyUrls[0]).searchParams.get('patient_id')).toBe('1')
  const card = page.locator('.desktop-card').first()
  await expect(card).toBeVisible()
  const box = await card.boundingBox()
  expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize().width + 1)
  await page.screenshot({ path: testInfo.outputPath('desktop-history.png'), fullPage: true })
  await page.getByText('AgentTeams 历史会诊').click()

  await expect(page).toHaveURL(/\/home\/consultation\/900\?patient_id=1$/)
  await expect(page.getByText('AgentTeams')).toBeVisible()
  await expect(page.locator('iframe.embed-iframe')).toHaveAttribute('src', '/agentteams/embed/conversation/embed-token')
})

test('AgentTeams launch reconciles a lost response without reposting', async ({ page }) => {
  const requestBodies = []
  let activeIntentCalls = 0
  await mockEmbedApis(page)
  await page.route('**/api/v1/consultation/agentteams/availability', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ configured: true, enabled: true, upsell: {} }),
    })
  })
  await page.route('**/api/v1/consultation/agentteams/start', route => {
    requestBodies.push(route.request().postDataJSON())
    route.fulfill({
      status: 202,
      contentType: 'application/json',
      body: JSON.stringify({
        conversation_id: 901,
        patient_id: 1,
        request_id: requestBodies[requestBodies.length - 1].request_id,
        provider: 'agentteams',
        launch_status: 'confirming',
        external_conversation_id: '1001',
        status: 'created',
      }),
    })
  })
  await page.route('**/api/v1/consultation/agentteams/launch-intents/active?**', route => {
    if (requestBodies.length === 0) {
      route.fulfill({ contentType: 'application/json', body: 'null' })
      return
    }
    activeIntentCalls += 1
    const accepted = activeIntentCalls > 1
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify(accepted ? {
        conversation_id: 901,
        patient_id: 1,
        request_id: requestBodies[0]?.request_id,
        provider: 'agentteams',
        launch_status: 'accepted',
        external_conversation_id: '1001',
        external_session_id: '2001',
        external_share_token: 'share-token',
        embed_url: '/agentteams/embed/conversation/embed-token',
        status: 'created',
      } : {
        conversation_id: 901,
        patient_id: 1,
        request_id: requestBodies[0]?.request_id,
        provider: 'agentteams',
        launch_status: 'confirming',
        status: 'created',
      }),
    })
  })
  await page.route('**/api/v1/consultation/agentteams/sessions/901**', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        conversation_id: 901,
        patient_id: 1,
        request_id: requestBodies[requestBodies.length - 1].request_id,
        provider: 'agentteams',
        launch_status: 'accepted',
        external_conversation_id: '1001',
        external_session_id: '2001',
        external_share_token: 'share-token',
        embed_url: '/agentteams/embed/conversation/embed-token',
        status: 'created',
      }),
    })
  })

  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })
  const startButton = page.getByRole('button', { name: '开始会诊' }).first()
  await expect(startButton).toBeVisible()

  await startButton.click()
  await expect.poll(() => requestBodies.length).toBe(1)
  const requestId = requestBodies[0].request_id
  expect(requestId).toMatch(/^[0-9a-f-]{36}$/i)
  await expect.poll(() => activeIntentCalls).toBeGreaterThan(1)
  expect(requestBodies).toHaveLength(1)
  await expect(page).toHaveURL(/\/home\/consultation\/901\?patient_id=1$/)
})

test('AgentTeams idempotency conflict discards the stale request id before retry', async ({ page }) => {
  const requestBodies = []
  await mockEmbedApis(page)
  await page.route('**/api/v1/consultation/agentteams/availability', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ configured: true, enabled: true, upsell: {} }),
    })
  })
  await page.route('**/api/v1/consultation/agentteams/start', route => {
    requestBodies.push(route.request().postDataJSON())
    if (requestBodies.length === 1) {
      route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: {
            error: 'agentteams_idempotency_conflict',
            message: 'raw remote conflict details',
          },
        }),
      })
      return
    }
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        conversation_id: 901,
        patient_id: 1,
        request_id: requestBodies[requestBodies.length - 1].request_id,
        provider: 'agentteams',
        launch_status: 'accepted',
        external_conversation_id: '1001',
        external_session_id: '2001',
        external_share_token: 'share-token',
        embed_url: '/agentteams/embed/conversation/embed-token',
        status: 'created',
      }),
    })
  })
  await page.route('**/api/v1/consultation/agentteams/sessions/901**', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        conversation_id: 901,
        provider: 'agentteams',
        external_conversation_id: '1001',
        external_session_id: '2001',
        embed_url: '/agentteams/embed/conversation/embed-token',
        status: 'created',
      }),
    })
  })

  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })
  const startButton = page.getByRole('button', { name: '开始会诊' }).first()
  await expect(startButton).toBeVisible()

  await startButton.click()
  await expect.poll(() => requestBodies.length).toBe(1)
  const staleRequestId = requestBodies[0].request_id
  await expect(page.getByText('会诊启动标识已失效')).toBeVisible()
  await expect(page.getByText('raw remote conflict details')).toHaveCount(0)

  await page.getByRole('button', { name: '关闭' }).click()
  await startButton.click()
  await expect.poll(() => requestBodies.length).toBe(2)
  expect(requestBodies[1].request_id).not.toBe(staleRequestId)
  expect(requestBodies[1].request_id).toMatch(/^[0-9a-f-]{36}$/i)
  await expect(page).toHaveURL(/\/home\/consultation\/901\?patient_id=1$/)
})

test('legacy generic consultation titles remain distinguishable on desktop and mobile', async ({ page }) => {
  await mockEmbedApis(page, {}, {
    conversationsByPatient: {
      1: [
        {
          id: 901,
          title: '虚拟会诊',
          patient_id: 1,
          provider: 'agentteams',
          external_session_status: 'completed',
          status: 'completed',
          created_at: '2026-07-09T10:00:00',
          updated_at: '2026-07-09T10:00:00',
        },
        {
          id: 902,
          title: 'AgentTeams 会诊',
          patient_id: 1,
          provider: 'agentteams',
          external_session_status: 'completed',
          status: 'completed',
          created_at: '2026-07-10T11:30:00',
          updated_at: '2026-07-10T11:30:00',
        },
        {
          id: 903,
          title: '待生成会诊标题',
          patient_id: 1,
          provider: 'agentteams',
          external_session_status: 'completed',
          status: 'completed',
          created_at: '2026-07-11T12:00:00',
          updated_at: '2026-07-11T12:00:00',
        },
      ],
    },
  })

  await page.setViewportSize({ width: 1366, height: 768 })
  await page.goto(`${baseURL}/home/consultation`)

  await expect(page.locator('.desktop-card-title')).toHaveText([
    '病情分析-#901',
    '病情分析-#902',
    '病情分析-#903',
  ])

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('.card-title')).toHaveText([
    '病情分析-#901',
    '病情分析-#902',
    '病情分析-#903',
  ])
})

test('AgentTeams history card fits the mobile viewport', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const counters = {}
  await mockEmbedApis(page, counters)

  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })

  const card = page.locator('.consultation-card').first()
  await expect(card).toBeVisible()
  const box = await card.boundingBox()
  expect(box.x).toBeGreaterThanOrEqual(0)
  expect(box.x + box.width).toBeLessThanOrEqual(page.viewportSize().width + 1)
  await expect(page.getByRole('button', { name: '切换患者' })).toHaveCount(0)
  await expect(page.getByPlaceholder('搜索会诊记录')).toHaveCount(0)
  await page.screenshot({ path: testInfo.outputPath('mobile-history.png'), fullPage: true })
})

test('numeric detail without patient context does not request AgentTeams', async ({ page }) => {
  const counters = {}
  await mockEmbedApis(page, counters)

  await page.goto(`${baseURL}/home/consultation/900`, { waitUntil: 'domcontentloaded' })

  await expect(page.getByText('此会诊记录缺少患者上下文，请从会诊历史重新进入')).toBeVisible()
  expect(counters.externalSessionCalls || 0).toBe(0)
})

test('legacy numeric detail without AgentTeams mapping shows error and does not request local session', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 })
  const counters = {}
  await mockEmbedApis(page, counters)
  await page.route('**/api/v1/consultation/agentteams/sessions/901**', route => {
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

  await page.goto(`${baseURL}/home/consultation/901?patient_id=1`, { waitUntil: 'domcontentloaded' })

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
  await page.route('**/api/v1/consultation/agentteams/sessions/902**', route => {
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

  await page.goto(`${baseURL}/home/consultation/902?patient_id=1`, { waitUntil: 'domcontentloaded' })

  await expect(page.getByText('AgentTeams 版本不兼容')).toBeVisible()
  await expect(page.getByText('当前 AgentTeams 版本不支持 OncoPath 集成，请升级 AgentTeams 后继续使用虚拟会诊。')).toBeVisible()
  await expect(page.getByText('agentteams.internal')).toHaveCount(0)

  await page.getByRole('button', { name: '查看处理方式' }).click()
  await expect(page.getByRole('button', { name: '查看升级说明' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'AgentTeams 版本不兼容' })).toBeVisible()
})

test('expired embed notification renews and replaces the iframe URL', async ({ page }) => {
  const counters = {}
  await mockEmbedApis(page, counters)
  let sessionReads = 0
  const renewQueries = []
  await page.route('**/api/v1/consultation/agentteams/sessions/900**', route => {
    sessionReads += 1
    const renew = new URL(route.request().url()).searchParams.get('renew')
    renewQueries.push(renew)
    const renewed = renew === 'true'
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        conversation_id: 900,
        provider: 'agentteams',
        external_conversation_id: '1001',
        external_session_id: '2001',
        embed_url: renewed
          ? '/agentteams/embed/conversation/renewed-token'
          : '/agentteams/embed/conversation/expired-token',
        status: 'monitoring',
      }),
    })
  })
  await page.route('**/agentteams/embed/conversation/expired-token', route => {
    route.fulfill({
      contentType: 'text/html',
      body: `<script>
        window.parent.postMessage({ type: 'oncopath:embed-renew-required' }, window.location.origin)
      </script>`,
    })
  })
  await page.route('**/agentteams/embed/conversation/renewed-token', route => {
    route.fulfill({
      contentType: 'text/html',
      body: '<main>renewed embed</main>',
    })
  })

  await page.goto(`${baseURL}/home/consultation/900?patient_id=1`, { waitUntil: 'domcontentloaded' })

  await expect(page.locator('iframe.embed-iframe')).toHaveAttribute(
    'src',
    '/agentteams/embed/conversation/renewed-token',
  )
  expect(sessionReads).toBeGreaterThanOrEqual(2)
  expect(renewQueries.slice(0, 2)).toEqual(['false', 'true'])
})
