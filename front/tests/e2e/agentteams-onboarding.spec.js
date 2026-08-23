import { test, expect } from '@playwright/test'

const baseURL = process.env.FRONT_BASE_URL || 'http://localhost:3000'
const AGENTTEAMS_REPO_URL = 'https://github.com/nickzhang1102/agentTeams'

async function mockCommonApis(page) {
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
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ conversations: [], total: 0, limit: 20, offset: 0 }),
    })
  })
  await page.route('**/api/v1/patients**', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify([{ patient_id: 1, patient_name: '测试患者', is_primary: true }]),
    })
  })
}

function mockAvailability(page, { configured, enabled }) {
  return page.route('**/api/v1/consultation/agentteams/availability', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        configured,
        enabled,
        base_url: configured ? 'https://agentteams.example.com' : '',
        capacity: null,
        upsell: {
          title: '需要部署 AgentTeams 项目',
          message: '部署 AgentTeams 后即可使用多 Agent 团队进行虚拟会诊分析。',
          demo_asset_url: '',
          cta_label: '获取 AgentTeams（开源自部署）',
          cta_url: AGENTTEAMS_REPO_URL,
        },
      }),
    })
  })
}

test('shows onboarding guide on first visit when AgentTeams is not configured', async ({ page }) => {
  await mockCommonApis(page)
  await mockAvailability(page, { configured: false, enabled: false })

  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })

  // 引导动画出现，步骤一介绍 AgentTeams 依赖
  await expect(page.getByText('虚拟会诊由 AgentTeams 提供')).toBeVisible()
  await expect(page.getByRole('button', { name: '下一步' })).toBeVisible()

  // 步骤二展示部署后效果示意 + 仓库 CTA
  await page.getByRole('button', { name: '下一步' }).click()
  await expect(page.getByText('部署后的虚拟会诊流程')).toBeVisible()
  await expect(page.getByRole('button', { name: '前往 GitHub 获取 AgentTeams' })).toBeVisible()

  // CTA 打开 agentTeams 公开仓库
  const popupPromise = page.waitForEvent('popup')
  await page.getByRole('button', { name: '前往 GitHub 获取 AgentTeams' }).click()
  const popup = await popupPromise
  expect(popup.url()).toBe(AGENTTEAMS_REPO_URL)

  // 完成引导后写入已读标记
  await page.getByRole('button', { name: '开始使用' }).click()
  await expect(page.getByText('虚拟会诊由 AgentTeams 提供')).toHaveCount(0)
  const seen = await page.evaluate(() => localStorage.getItem('oncopath_agentteams_guide_seen'))
  expect(seen).toBe('1')
})

test('onboarding guide does not reappear after being dismissed', async ({ page }) => {
  await mockCommonApis(page)
  await mockAvailability(page, { configured: false, enabled: false })
  await page.addInitScript(() => {
    localStorage.setItem('oncopath_agentteams_guide_seen', '1')
  })

  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })

  await expect(page.getByRole('button', { name: '开始会诊' }).first()).toBeVisible()
  await expect(page.getByText('虚拟会诊由 AgentTeams 提供')).toHaveCount(0)
})

test('onboarding guide never shows when AgentTeams is configured', async ({ page }) => {
  await mockCommonApis(page)
  await mockAvailability(page, { configured: true, enabled: true })

  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })

  await expect(page.getByRole('button', { name: '开始会诊' }).first()).toBeVisible()
  await expect(page.getByText('虚拟会诊由 AgentTeams 提供')).toHaveCount(0)
})

test('consultation status bar reflects AgentTeams availability', async ({ page }) => {
  await mockCommonApis(page)
  await page.addInitScript(() => {
    localStorage.setItem('oncopath_agentteams_guide_seen', '1')
  })

  // 未部署：状态栏显示未部署 + agentTeams 仓库链接
  await mockAvailability(page, { configured: false, enabled: false })
  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })
  await expect(page.getByText('虚拟会诊引擎 AgentTeams 未部署')).toBeVisible()
  const offlineLink = page.locator('.at-status-bar').getByRole('link')
  await expect(offlineLink).toHaveAttribute('href', AGENTTEAMS_REPO_URL)

  // 已连接：状态栏显示已连接，链接保留
  await mockAvailability(page, { configured: true, enabled: true })
  await page.goto(`${baseURL}/home/consultation`, { waitUntil: 'domcontentloaded' })
  await expect(page.getByText('虚拟会诊引擎 AgentTeams 已连接')).toBeVisible()
  const onlineLink = page.locator('.at-status-bar').getByRole('link')
  await expect(onlineLink).toHaveAttribute('href', AGENTTEAMS_REPO_URL)
})
