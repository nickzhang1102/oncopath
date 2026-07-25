/**
 * 核心流程 E2E 测试
 *
 * 覆盖：登录、注册、主页导航、患者切换、登出
 * 使用 Playwright request API 动态创建测试用户
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_core_${RUN_ID}`,
  password: 'E2e@Test123',
};

// 缓存 token，避免重复登录触发限流
let cachedToken = '';

async function getOrCreateToken(request) {
  if (cachedToken) return cachedToken;

  // 注册（如已存在忽略 400）
  await request.post(`${API_URL}/auth/register`, {
    data: { username: TEST_CREDENTIALS.username, password: TEST_CREDENTIALS.password },
  }).catch(() => {});

  // 登录
  const loginResp = await request.post(`${API_URL}/auth/login`, {
    data: { username: TEST_CREDENTIALS.username, password: TEST_CREDENTIALS.password },
  });
  expect(loginResp.ok()).toBeTruthy();
  cachedToken = (await loginResp.json()).access_token;
  return cachedToken;
}

test.describe('核心流程 E2E', () => {

  // ---- 注册 + 登录 ----

  test('通过 UI 注册新用户', async ({ page }) => {
    const uniqUser = `e2e_reg_${RUN_ID}`;
    await page.goto(`${BASE_URL}/login`);

    // 切换到注册模式
    await page.getByText('没有账号？立即注册').click();

    // 填写注册表单
    await page.getByRole('textbox', { name: '用户名' }).fill(uniqUser);
    await page.getByRole('textbox', { name: '密码' }).first().fill('E2e@Test123');
    await page.getByRole('textbox', { name: '确认密码' }).fill('E2e@Test123');

    // 提交
    await page.getByRole('button', { name: '注册' }).click();

    // 注册成功后应跳转到主页
    await page.waitForURL(/\/home\/main/, { timeout: 15000 });
    await expect(page).toHaveURL(/\/home\/main/);
  });

  test('通过 UI 登录已有用户', async ({ page, request }) => {
    const uniqUser = `e2e_login_${RUN_ID}`;
    // 先通过 API 确保用户存在
    await request.post(`${API_URL}/auth/register`, {
      data: { username: uniqUser, password: 'E2e@Test123' },
    }).catch(() => {});

    // UI 登录
    await page.goto(`${BASE_URL}/login`);
    await page.getByRole('textbox', { name: '用户名' }).fill(uniqUser);
    await page.getByRole('textbox', { name: '密码' }).fill('E2e@Test123');
    await page.getByRole('button', { name: '登录' }).click();

    await page.waitForURL(/\/home\/main/, { timeout: 15000 });
    await expect(page).toHaveURL(/\/home\/main/);
  });

  // ---- 侧边栏导航 ----

  test.describe('已登录后侧边栏导航', () => {
    test.beforeEach(async ({ page, request }) => {
      const token = await getOrCreateToken(request);

      // 在页面加载前注入 localStorage，确保 Vue 初始化时就读到 token
      await page.addInitScript((t) => {
        localStorage.setItem('token', t);
        localStorage.setItem('refresh_token', 'test-refresh');
        localStorage.setItem('onboarding_completed', '1');
      }, token);

      await page.goto(`${BASE_URL}/home/main`);
      await page.waitForURL(/\/home\/main/, { timeout: 10000 });
    });

    test('侧边栏链接可导航到时间线页面', async ({ page }) => {
      await page.getByRole('link', { name: '时间线' }).click();
      await page.waitForURL(/\/home\/timeline/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/home\/timeline/);
    });

    test('侧边栏链接可导航到检验报告页面', async ({ page }) => {
      await page.getByRole('link', { name: '检验报告' }).click();
      await page.waitForURL(/\/home\/reports/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/home\/reports/);
    });

    test('侧边栏链接可导航到虚拟会诊页面', async ({ page }) => {
      await page.getByRole('link', { name: '虚拟会诊' }).click();
      await page.waitForURL(/\/home\/consultation/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/home\/consultation/);
    });

    test('侧边栏链接可导航到用药记录页面', async ({ page }) => {
      await page.getByRole('link', { name: '用药记录' }).click();
      await page.waitForURL(/\/home\/medication/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/home\/medication/);
    });

    test('侧边栏链接可导航到全局搜索页面', async ({ page }) => {
      await page.getByRole('link', { name: '全局搜索' }).click();
      await page.waitForURL(/\/home\/search/, { timeout: 10000 });
      await expect(page).toHaveURL(/\/home\/search/);
    });
  });

  // ---- 登出 ----

  test('登出后跳转到登录页', async ({ page, request }) => {
    const token = await getOrCreateToken(request);

    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
      localStorage.setItem('onboarding_completed', '1');
    }, token);

    await page.goto(`${BASE_URL}/home/profile`);
    await page.waitForURL(/\/home\/profile/, { timeout: 10000 });

    // 点击退出登录按钮
    await page.getByRole('button', { name: '退出登录' }).click();

    // 确认退出对话框
    await page.getByRole('button', { name: '确认' }).click();

    // 应跳转到登录页
    await page.waitForURL(/\/login/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/login/);
  });
});
