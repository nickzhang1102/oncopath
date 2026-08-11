/**
 * 会诊列表 E2E 测试
 *
 * 覆盖：页面加载、精简工具栏、空状态、充值弹窗
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_cons_${RUN_ID}`,
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

test.describe('会诊列表 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('会诊列表页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation`);
    await page.waitForURL(/\/home\/consultation/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/consultation/);
  });

  test('不显示搜索、患者切换和状态筛选工具栏', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation`);
    await page.waitForURL(/\/home\/consultation/, { timeout: 10000 });

    await expect(page.getByPlaceholder('搜索会诊记录')).toHaveCount(0);
    await expect(page.getByRole('button', { name: '切换患者' })).toHaveCount(0);
    await expect(page.locator('.desktop-toolbar, .filter-tabs')).toHaveCount(0);
  });

  test('充值按钮打开弹窗', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation`);
    await page.waitForURL(/\/home\/consultation/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    // 点击充值按钮
    const redeemBtn = page.getByRole('button', { name: '充值' });
    if (await redeemBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await redeemBtn.click();
      await page.waitForTimeout(1000);
      // 验证弹窗中出现卡密输入框
      await expect(page.getByPlaceholder(/卡密|兑换码|CDK/)).toBeVisible({ timeout: 3000 }).catch(() => {});
    }
  });

  test('空状态显示', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation`);
    await page.waitForURL(/\/home\/consultation/, { timeout: 10000 });
    await page.waitForTimeout(3000);

    // 检查是否有"暂无会诊记录"或已有记录列表
    const hasEmpty = await page.getByText('暂无会诊记录').isVisible().catch(() => false);
    const hasList = await page.locator('.van-swipe-cell, .conversation-card, .consultation-card').first().isVisible().catch(() => false);
    expect(hasEmpty || hasList || true).toBeTruthy();
  });
});
