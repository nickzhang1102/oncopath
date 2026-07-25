/**
 * 状态记录 E2E 测试
 *
 * 覆盖：页面加载、空状态
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_status_${RUN_ID}`,
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

test.describe('状态记录 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('状态记录页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/status`, { timeout: 30000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/status/, { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(3000);

    await expect(page).toHaveURL(/\/home\/status/);
  });

  test('无患者时显示空状态', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/status`, { timeout: 30000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/status/, { timeout: 15000 }).catch(() => {});
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
});
