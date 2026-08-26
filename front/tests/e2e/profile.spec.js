/**
 * 个人中心 E2E 测试
 *
 * 覆盖：用户信息显示、功能列表导航、退出登录
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_profile_${RUN_ID}`,
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

test.describe('个人中心 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('个人中心页面加载显示用户信息', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile`);
    await page.waitForURL(/\/home\/profile/, { timeout: 10000 });

    // 用户名应显示
    await expect(page.locator('.user-name')).toBeVisible({ timeout: 5000 });
    // 退出登录按钮
    await expect(page.getByRole('button', { name: '退出登录' })).toBeVisible();
  });

  test('功能列表导航项可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile`);
    await page.waitForURL(/\/home\/profile/, { timeout: 10000 });

    await expect(page.getByRole('button', { name: /病人管理/ })).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.van-cell').filter({ hasText: '数据导出' })).toBeVisible();

    // 设置
    await expect(page.locator('.van-cell').filter({ hasText: '个人信息' })).toBeVisible();
    await expect(page.locator('.van-cell').filter({ hasText: '修改密码' })).toBeVisible();
    await expect(page.locator('.van-cell').filter({ hasText: '外观模式' })).toBeVisible();
  });

  test('点击修改密码跳转密码页面', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile`);
    await page.waitForURL(/\/home\/profile/, { timeout: 10000 });

    await page.getByText('修改密码').click();
    await page.waitForURL(/\/home\/profile\/password/, { timeout: 10000 });
  });

  test('外观模式选择器弹出', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile`);
    await page.waitForURL(/\/home\/profile/, { timeout: 10000 });

    // 点击外观模式
    await page.getByText(/外观模式/).click();
    await page.waitForTimeout(1000);

    // 主题选择器（用 .theme-picker 容器精确匹配）
    await expect(page.locator('.theme-picker').getByText('浅色')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.theme-picker').getByText('深色')).toBeVisible();
    await expect(page.locator('.theme-picker').getByText('跟随系统')).toBeVisible();
  });

  test('退出登录流程', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile`);
    await page.waitForURL(/\/home\/profile/, { timeout: 10000 });

    // 点击退出登录
    await page.getByRole('button', { name: '退出登录' }).click();

    // 确认对话框
    await page.waitForTimeout(1000);
    const confirmBtn = page.getByRole('button', { name: '确定' });
    if (await confirmBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await confirmBtn.click();
      // 应跳转到登录页
      await page.waitForURL(/\/login/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/login/);
    }
  });

  test('版本信息显示', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/profile`);
    await page.waitForURL(/\/home\/profile/, { timeout: 10000 });

    await expect(page.getByText('版本 2.0.0')).toBeVisible({ timeout: 5000 });
  });
});
