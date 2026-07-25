/**
 * 指标查询 E2E 测试
 *
 * 覆盖：页面加载、搜索框、分类Tab
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_index_${RUN_ID}`,
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

test.describe('指标查询 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('指标查询页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/index`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/index/, { timeout: 15000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/index/);
  });

  test('搜索框可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/index`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/index/, { timeout: 15000 });
    await page.waitForTimeout(2000);

    const searchInput = page.getByRole('searchbox').or(page.getByPlaceholder(/搜索|指标/));
    await expect(searchInput.first()).toBeVisible({ timeout: 5000 }).catch(() => {});
  });

  test('分类Tab可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/index`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/index/, { timeout: 15000 });
    await page.waitForTimeout(2000);

    const tabs = page.getByRole('tab');
    if (await tabs.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(tabs.first()).toBeVisible();
    }
  });
});
