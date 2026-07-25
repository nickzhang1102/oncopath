import { test, expect } from '@playwright/test'

const API_URL = 'http://localhost:8000/api/v1'
const RUN_ID = Date.now()
const PASSWORD = 'E2e@Test123'

let session

async function getSession(request) {
  if (session) return session

  const username = `e2e_ui_regression_${RUN_ID}`
  await request.post(`${API_URL}/auth/register`, {
    data: { username, password: PASSWORD },
  })
  const login = await request.post(`${API_URL}/auth/login`, {
    data: { username, password: PASSWORD },
  })
  expect(login.ok()).toBeTruthy()
  const token = (await login.json()).access_token
  await request.post(`${API_URL}/patients`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { patient_name: `界面回归患者${RUN_ID}`, gender: 'male' },
  })
  session = { token }
  return session
}

async function rect(locator) {
  return locator.evaluate((element) => {
    const value = element.getBoundingClientRect()
    return {
      left: value.left,
      top: value.top,
      right: value.right,
      bottom: value.bottom,
    }
  })
}

function overlap(a, b) {
  return {
    width: Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)),
    height: Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top)),
  }
}

test.describe('前端双端界面回归', () => {
  test('完成新手引导后关闭弹窗并恢复页面滚动', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-chromium', '移动端覆盖完整引导闭环')
    let patientCreated = false
    await page.route('**/api/v1/**', async (route) => {
      const request = route.request()
      const pathname = new URL(request.url()).pathname
      if (pathname.endsWith('/accounts/me')) {
        return route.fulfill({ json: { account_id: 1, username: 'onboarding-user', account_type: 'user' } })
      }
      if (pathname.endsWith('/patients') && request.method() === 'POST') {
        patientCreated = true
        return route.fulfill({ json: { patient_id: 1, patient_name: '引导回归患者', gender: 'male', is_primary: true } })
      }
      if (pathname.endsWith('/patients')) {
        return route.fulfill({
          json: patientCreated
            ? [{ patient_id: 1, patient_name: '引导回归患者', gender: 'male', is_primary: true }]
            : [],
        })
      }
      return route.fulfill({ json: {} })
    })
    await page.addInitScript(() => {
      localStorage.setItem('token', 'onboarding-test-token')
      localStorage.removeItem('onboarding_completed')
      localStorage.removeItem('currentPatientId')
    })
    await page.goto('/home/main')
    await page.getByRole('heading', { name: '欢迎来到 OncoPath' }).waitFor()

    await page.getByPlaceholder('请输入患者姓名').fill('引导回归患者')
    await page.getByRole('button', { name: '创建患者并继续' }).click()
    await page.getByRole('heading', { name: '上传检验报告' }).waitFor()
    await page.getByRole('button', { name: '稍后再说' }).click()
    await page.getByRole('button', { name: '开始使用' }).click()

    await expect(page.getByRole('heading', { name: '开始使用' })).not.toBeVisible()
    await expect.poll(() => page.evaluate(() => document.body.classList.contains('van-overflow-hidden'))).toBe(false)
  })

  test('移动端全局控件不覆盖页面操作和弹窗', async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-chromium', '仅检查移动布局')
    const { token } = await getSession(request)
    await page.addInitScript((value) => {
      localStorage.setItem('token', value)
      localStorage.setItem('refresh_token', 'test-refresh')
      localStorage.setItem('onboarding_completed', '1')
    }, token)

    await page.goto('/home/main')
    const drawerOverlap = overlap(
      await rect(page.locator('.drawer-trigger-btn')),
      await rect(page.locator('.quick-action-bar .action-item').first()),
    )
    expect(drawerOverlap.width * drawerOverlap.height).toBe(0)

    await page.goto('/home/profile')
    await page.getByText(/外观模式/).click()
    const systemOption = page.locator('.theme-picker__option').last()
    await expect(systemOption).toBeVisible()
    await page.waitForTimeout(350)
    const optionHit = await systemOption.evaluate((element) => {
      const box = element.getBoundingClientRect()
      return element.contains(document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2))
    })
    expect(optionHit).toBe(true)
    await page.keyboard.press('Escape')

    await page.goto('/home/patient-management')
    await page.waitForTimeout(500)
    const bubbleOverlap = overlap(
      await rect(page.locator('.van-floating-bubble')),
      await rect(page.locator('.van-tabbar')),
    )
    expect(bubbleOverlap.width * bubbleOverlap.height).toBe(0)

    await page.getByRole('button', { name: '编辑' }).click()
    const updateButton = page.getByRole('button', { name: '更新' })
    await updateButton.scrollIntoViewIfNeeded()
    await page.waitForTimeout(350)
    const updateHit = await updateButton.evaluate((element) => {
      const box = element.getBoundingClientRect()
      return element.contains(document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2))
    })
    expect(updateHit).toBe(true)
  })
})
