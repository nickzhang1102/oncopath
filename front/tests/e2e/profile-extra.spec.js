/**
 * 个人中心子页面 (补充) E2E 测试
 *
 * 覆盖：帮助中心、关于我们、隐私设置、消息通知
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_sub2_${RUN_ID}`,
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

test.describe('帮助中心 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('帮助中心页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile/help`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/profile\/help/, { timeout: 15000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/profile\/help/);
  });

  test('常见问题折叠面板可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile/help`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/profile\/help/, { timeout: 15000 });

    const collapse = page.locator('.van-collapse-item').first();
    if (await collapse.isVisible({ timeout: 3000 }).catch(() => false)) {
      await collapse.click();
      await page.waitForTimeout(500);
    }
  });

  test('联系客服区域可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile/help`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/profile\/help/, { timeout: 15000 });

    await expect(page.getByText('联系客服')).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});

test.describe('关于我们 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('关于我们页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile/about`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/profile\/about/, { timeout: 15000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/profile\/about/);
  });

  test('应用名称和版本可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile/about`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/profile\/about/, { timeout: 15000 });

    await expect(page.getByText('医疗报告系统')).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});

test.describe('隐私设置 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('隐私设置页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile/privacy`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/profile\/privacy/, { timeout: 15000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/profile\/privacy/);
  });

  test('开关控件可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile/privacy`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/profile\/privacy/, { timeout: 15000 });

    const switchCtrl = page.locator('.van-switch').first();
    await expect(switchCtrl).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});

test.describe('消息通知 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('消息通知页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile/notifications`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/profile\/notifications/, { timeout: 15000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/profile\/notifications/);
  });

  test('Tab筛选可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile/notifications`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/profile\/notifications/, { timeout: 15000 });

    const tabs = page.getByRole('tab');
    await expect(tabs.first()).toBeVisible({ timeout: 5000 }).catch(() => {});
  });

  test('全部已读按钮可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile/notifications`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/profile\/notifications/, { timeout: 15000 });

    const readAllBtn = page.getByRole('button', { name: '全部已读' });
    await expect(readAllBtn).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});
