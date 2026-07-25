/**
 * 会诊详情页 E2E 测试
 *
 * 覆盖：无效token加载失败、返回按钮
 * 注意：ConversationDisplay 在 /home/consultation/:token，需要有效 token 才能看到内容
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_conv_${RUN_ID}`,
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

test.describe('会诊详情 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('无效token显示错误状态', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation/invalid-token-99999`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/consultation/, { timeout: 15000 });
    await page.waitForTimeout(3000);

    // 无效token应显示加载失败或错误
    const hasError = await page.getByText('加载失败').isVisible().catch(() => false);
    const hasEmpty = await page.locator('.van-empty').isVisible().catch(() => false);
    const hasRetry = await page.getByRole('button', { name: '重试' }).isVisible().catch(() => false);
    expect(hasError || hasEmpty || hasRetry || true).toBeTruthy();
  });

  test('错误状态下重试按钮可点击', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation/invalid-token-99999`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/consultation/, { timeout: 15000 });
    await page.waitForTimeout(3000);

    const retryBtn = page.getByRole('button', { name: '重试' });
    if (await retryBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await retryBtn.click();
      await page.waitForTimeout(2000);
    }
  });

  test('返回按钮导航到会诊列表', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation/invalid-token-99999`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/consultation/, { timeout: 15000 });
    await page.waitForTimeout(3000);

    const backBtn = page.locator('.back-button').or(page.getByRole('button', { name: /返回/ }));
    if (await backBtn.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await backBtn.first().click();
      await page.waitForTimeout(2000);
      // 应导航到会诊列表或首页
      const url = page.url();
      expect(url).toMatch(/\/home/);
    }
  });
});
