import { test, expect } from '@playwright/test'

const baseURL = process.env.FRONT_BASE_URL || 'http://localhost:3000'

async function mockUploadApis(page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'test-token')
    localStorage.setItem('refreshToken', 'test-refresh')
    localStorage.setItem('currentPatientId', '1')
  })

  await page.route('**/api/v1/accounts/notifications/stream', route => {
    route.fulfill({ status: 204, body: '' })
  })
  await page.route('**/api/v1/accounts/notifications**', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ items: [], total: 0, unread_count: 0 }),
    })
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
      body: JSON.stringify([
        { patient_id: 1, patient_name: '测试患者', is_primary: true },
      ]),
    })
  })
  await page.route('**/api/v1/image_reports/categories', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })
  await page.route('**/api/v1/image_reports/stats?**', route => {
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        total_count: 4,
        category_stats: [],
        hospital_stats: [
          { hospital: '市人民医院', count: 1 },
          { hospital: '协和医院', count: 3 },
        ],
        recent_reports: [],
      }),
    })
  })
}

test.describe('报告上传输入增强', () => {
  test.beforeEach(async ({ page }) => {
    await mockUploadApis(page)
  })

  test('桌面端可直接输入检查日期', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await page.goto(`${baseURL}/home/image-report`)

    const dateInput = page.locator('input[type="date"][aria-label="检查日期"]')
    await expect(dateInput).toBeVisible()
    await dateInput.fill('2026-08-15')
    await expect(dateInput).toHaveValue('2026-08-15')
  })

  test('可从当前患者的历史医院中选择并保留手动输入', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await page.goto(`${baseURL}/home/image-report`)

    const hospitalInput = page.getByPlaceholder('请输入医院名称')
    await expect(page.getByRole('button', { name: '历史医院' })).toBeVisible()
    await page.getByRole('button', { name: '历史医院' }).click()

    const hospitalNames = page.locator('.van-action-sheet__name')
    await expect(hospitalNames).toHaveText(['协和医院', '市人民医院'])
    await page.getByRole('button', { name: /协和医院/ }).click()
    await expect(hospitalInput).toHaveValue('协和医院')

    await hospitalInput.fill('新医院')
    await expect(hospitalInput).toHaveValue('新医院')
  })

  test('移动端继续使用滑动日期选择器', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(`${baseURL}/home/image-report`)

    await expect(page.locator('input[type="date"]')).toHaveCount(0)
    await page.getByPlaceholder('请选择检查日期').click()
    await expect(page.getByText('选择检查日期', { exact: true })).toBeVisible()
    await expect(page.locator('.van-picker-column')).toHaveCount(3)
  })
})
