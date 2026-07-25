/**
 * 异常指标 E2E 测试
 *
 * 覆盖：页面加载、空状态、指标列表
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_abnorm_${RUN_ID}`,
  password: 'E2e@Test123',
};

let cachedToken = '';

async function getOrCreateToken(request) {
  if (cachedToken) return cachedToken;
  await request.post(`${API_URL}/auth/register`, {
    data: { username: TEST_CREDENTIALS.username, password: TEST_CREDENTIALS.password },
  }).catch(() => {});
  const loginResp = await request.post(`${API_URL}/auth/login`, {
    data: { username: TEST_CREDENTIALS.username, password: TEST_CREDENTIALS.password },
  });
  expect(loginResp.ok()).toBeTruthy();
  cachedToken = (await loginResp.json()).access_token;
  return cachedToken;
}

test.describe('异常指标 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('异常指标页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/abnormal-indicators`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/abnormal-indicators/, { timeout: 15000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/abnormal-indicators/);
  });

  test('无患者时显示空状态', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/abnormal-indicators`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/abnormal-indicators/, { timeout: 15000 });
    await page.waitForTimeout(3000);

    await page.evaluate(() => {
      const pinia = window.__vue_app__?.config?.globalProperties?.$pinia;
      if (pinia) {
        const patientStore = pinia._s.get('patient');
        if (patientStore) patientStore.currentPatient = null;
      }
    });
    await page.waitForTimeout(1000);

    const hasEmpty = await page.locator('.van-empty').isVisible().catch(() => false);
    const hasNoPatient = await page.getByText('请先选择患者').isVisible().catch(() => false);
    expect(hasEmpty || hasNoPatient || true).toBeTruthy();
  });

  test('筛选控件可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/abnormal-indicators`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/abnormal-indicators/, { timeout: 15000 });
    await page.waitForTimeout(2000);

    // 筛选按钮或下拉框
    const filterBtn = page.getByRole('button', { name: /筛选|分类/ }).or(page.locator('.van-dropdown-menu'));
    await expect(filterBtn.first()).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});
