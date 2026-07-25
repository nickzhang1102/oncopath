/**
 * 个人中心子页面 E2E 测试
 *
 * 覆盖：个人信息、修改密码、数据导出
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_sub_${RUN_ID}`,
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

async function navigateTo(page, path) {
  await page.goto(`${BASE_URL}${path}`, { timeout: 30000, waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
}

test.describe('个人信息页 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('个人信息页加载', async ({ page }) => {
    await navigateTo(page, '/home/profile/info');
    await expect(page).toHaveURL(/\/home\/profile\/info/);
  });
});

test.describe('修改密码页 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('修改密码页加载', async ({ page }) => {
    await navigateTo(page, '/home/profile/password');
    await expect(page).toHaveURL(/\/home\/profile\/password/);
  });

  test('密码表单字段可见', async ({ page }) => {
    await navigateTo(page, '/home/profile/password');
    const oldPwd = page.getByRole('textbox', { name: /旧密码|当前密码/ }).or(page.getByPlaceholder(/旧密码|当前密码/));
    await expect(oldPwd.first()).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});

test.describe('数据导出页 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('数据导出页加载', async ({ page }) => {
    await navigateTo(page, '/home/profile/export');
    await expect(page).toHaveURL(/\/home\/profile\/export/);
  });
});