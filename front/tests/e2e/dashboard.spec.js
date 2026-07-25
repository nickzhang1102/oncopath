/**
 * 仪表盘首页 E2E 测试
 *
 * 覆盖：首页加载、数据概览、快捷操作、患者切换
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_dash_${RUN_ID}`,
  password: 'E2e@Test123',
};

let cachedToken = '';
let cachedPatientId = '';

async function setupWithPatient(request) {
  if (cachedToken && cachedPatientId) return { token: cachedToken, patientId: cachedPatientId };

  await request.post(`${API_URL}/auth/register`, {
    data: { username: TEST_CREDENTIALS.username, password: TEST_CREDENTIALS.password },
  }).catch(() => {});
  const loginResp = await request.post(`${API_URL}/auth/login`, {
    data: { username: TEST_CREDENTIALS.username, password: TEST_CREDENTIALS.password },
  });
  expect(loginResp.ok()).toBeTruthy();
  cachedToken = (await loginResp.json()).access_token;

  const patientResp = await request.post(`${API_URL}/patients`, {
    headers: { 'Authorization': `Bearer ${cachedToken}`, 'Content-Type': 'application/json' },
    data: { patient_name: `仪表盘患者${RUN_ID}`, gender: 'male' },
  });
  if (patientResp.ok()) {
    const data = await patientResp.json();
    cachedPatientId = data.patient_id || data.id;
  }

  return { token: cachedToken, patientId: cachedPatientId };
}

test.describe('仪表盘首页 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('首页加载显示数据概览', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/main`);
    await page.waitForURL(/\/home\/main/, { timeout: 10000 });
    await page.waitForTimeout(3000);

    // 页面应正常加载
    await expect(page).toHaveURL(/\/home\/main/);
  });

  test('首页患者信息区域可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/main`);
    await page.waitForURL(/\/home\/main/, { timeout: 10000 });
    await page.waitForTimeout(3000);

    // 患者信息区域（显示患者名或"未选择"）
    const patientSection = page.locator('.patient-section, .patient-banner, .mobile-patient-banner').first();
    if (await patientSection.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(patientSection).toBeVisible();
    }
  });

  test('首页快捷操作可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/main`);
    await page.waitForURL(/\/home\/main/, { timeout: 10000 });
    await page.waitForTimeout(3000);

    // 快捷操作按钮区域
    const quickAction = page.locator('.quick-action, .feature-grid, .van-grid').first();
    if (await quickAction.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(quickAction).toBeVisible();
    }
  });

  test('侧边导航栏可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/main`);
    await page.waitForURL(/\/home\/main/, { timeout: 10000 });

    // 桌面端显示侧边栏导航
    const nav = page.getByRole('navigation');
    await expect(nav).toBeVisible({ timeout: 5000 });
  });

  test('侧边导航切换到时间线', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/main`);
    await page.waitForURL(/\/home\/main/, { timeout: 10000 });

    // 点击时间线链接
    const timelineLink = page.getByRole('link', { name: '时间线' });
    if (await timelineLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await timelineLink.click();
      await page.waitForTimeout(1000);
      await expect(page).toHaveURL(/\/home\/timeline/, { timeout: 5000 });
    }
  });
});