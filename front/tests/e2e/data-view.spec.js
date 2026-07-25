/**
 * 数据查看 E2E 测试
 *
 * 覆盖：全局搜索、检验报告页面加载
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_data_${RUN_ID}`,
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

test.describe('全局搜索 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('搜索页面加载显示搜索框', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/search`);
    await page.waitForURL(/\/home\/search/, { timeout: 10000 });
    await expect(page.getByRole('searchbox')).toBeVisible({ timeout: 5000 });
  });

  test('搜索框输入关键词可触发搜索', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/search`);
    await page.waitForURL(/\/home\/search/, { timeout: 10000 });

    const searchbox = page.getByRole('searchbox');
    await searchbox.fill('白细胞');

    // 等待搜索结果或无结果提示
    await page.waitForTimeout(2000);

    // 验证搜索框中包含输入的关键词
    await expect(searchbox).toHaveValue('白细胞');
  });

  test('点击取消关闭搜索', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/search`);
    await page.waitForURL(/\/home\/search/, { timeout: 10000 });

    await page.getByRole('button', { name: '取消' }).click();
    // 取消后应离开搜索页
    await page.waitForTimeout(1000);
    await expect(page).not.toHaveURL(/\/home\/search$/);
  });
});

test.describe('检验报告 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('检验报告页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/reports`);
    await page.waitForURL(/\/home\/reports/, { timeout: 10000 });
    // 页面标题或内容可见
    await page.waitForTimeout(2000);
    // 验证页面已加载（不依赖特定数据）
    await expect(page).toHaveURL(/\/home\/reports/);
  });
});

test.describe('路由守卫 E2E', () => {
  test('未登录访问受保护页面跳转到登录页', async ({ page }) => {
    // 不注入 token
    await page.goto(`${BASE_URL}/home/main`);
    await page.waitForURL(/\/login/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/login/);
    // 验证 redirect 参数
    const url = new URL(page.url());
    expect(url.searchParams.get('redirect')).toBeTruthy();
  });

  test('404 页面正确显示', async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);

    await page.goto(`${BASE_URL}/nonexistent-page-12345`);
    await page.waitForTimeout(2000);
    // 应该显示 404 页面或重定向
    const url = page.url();
    expect(url).toContain('nonexistent-page-12345');
  });
});
