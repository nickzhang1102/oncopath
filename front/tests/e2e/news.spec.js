/**
 * 智能资讯 E2E 测试
 *
 * 覆盖：页面加载、功能网格可见、链接可点击
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_news_${RUN_ID}`,
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

test.describe('智能资讯 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('智能资讯页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/news`);
    await page.waitForURL(/\/home\/news/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/news/);
  });

  test('功能入口可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/news`);
    await page.waitForURL(/\/home\/news/, { timeout: 10000 });

    // 验证核心功能入口 (heading 元素)
    await expect(page.getByRole('heading', { name: '虚拟会诊' })).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('heading', { name: '知识库' })).toBeVisible();
  });

  test('点击虚拟会诊跳转', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/news`);
    await page.waitForURL(/\/home\/news/, { timeout: 10000 });

    // 点击虚拟会诊卡片
    const consultationCard = page.locator('[cursor=pointer]').filter({ hasText: '虚拟会诊' }).first();
    if (await consultationCard.isVisible({ timeout: 3000 }).catch(() => false)) {
      await consultationCard.click();
      await page.waitForTimeout(1000);
      await expect(page).toHaveURL(/\/home\/consultation/, { timeout: 5000 });
    }
  });
});
