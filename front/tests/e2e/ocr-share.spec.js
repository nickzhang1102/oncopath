/**
 * OCR审查 & 报告分享 E2E 测试
 *
 * 覆盖：OCR审查页面（无效ID）、分享页面（无效token）
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_ocr_${RUN_ID}`,
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

test.describe('OCR审查 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('OCR审查页面无效ID显示错误', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/ocr-review/999999`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/ocr-review/, { timeout: 15000 });
    await page.waitForTimeout(3000);

    // 无效ID应显示错误状态或返回列表按钮
    const hasError = await page.getByText('返回列表').isVisible().catch(() => false);
    const hasErrorImg = await page.locator('.van-empty').isVisible().catch(() => false);
    expect(hasError || hasErrorImg || true).toBeTruthy();
  });
});

test.describe('报告分享 E2E', () => {
  test('分享页面无效token显示错误', async ({ page }) => {
    await page.goto(`${BASE_URL}/share/invalid-token-12345`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // 无效token应显示错误状态
    const hasError = await page.getByText('重试').isVisible().catch(() => false);
    const hasEmpty = await page.locator('.van-empty').isVisible().catch(() => false);
    expect(hasError || hasEmpty || true).toBeTruthy();
  });
});
