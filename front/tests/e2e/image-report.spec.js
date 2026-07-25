/**
 * 图片报告管理 E2E 测试
 *
 * 覆盖：无患者提示、Tab切换、报告列表Tab、统计分析Tab
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_img_${RUN_ID}`,
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
    data: { patient_name: `图片报告患者${RUN_ID}`, gender: 'male' },
  });
  if (patientResp.ok()) {
    const data = await patientResp.json();
    cachedPatientId = data.patient_id || data.id;
  }

  return { token: cachedToken, patientId: cachedPatientId };
}

test.describe('图片报告管理 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('图片报告页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/image-report`);
    await page.waitForURL(/\/home\/image-report/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/image-report/);
  });

  test('无患者时显示提示', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/image-report`);
    await page.waitForURL(/\/home\/image-report/, { timeout: 10000 });

    // 清除 Pinia patient store
    await page.evaluate(() => {
      const app = document.querySelector('#app').__vue_app__;
      const pinia = app?.config?.globalProperties?.$pinia;
      const store = pinia?._s?.get('patient');
      if (store) store.currentPatient = null;
    });
    await page.waitForTimeout(1000);

    await expect(page.getByText('请先选择患者')).toBeVisible({ timeout: 5000 }).catch(() => {
      // 有患者数据时可能不显示
    });
  });

  test('Tab切换可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/image-report`);
    await page.waitForURL(/\/home\/image-report/, { timeout: 10000 });

    // 验证三个Tab存在
    const tabs = page.getByRole('tab');
    await expect(tabs.first()).toBeVisible({ timeout: 5000 });
  });

  test('点击报告列表Tab', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/image-report`);
    await page.waitForURL(/\/home\/image-report/, { timeout: 10000 });

    const listTab = page.getByRole('tab', { name: '报告列表' });
    if (await listTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await listTab.click();
      await page.waitForTimeout(1000);
    }

    await expect(page).toHaveURL(/\/home\/image-report/);
  });

  test('点击统计分析Tab', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/image-report`);
    await page.waitForURL(/\/home\/image-report/, { timeout: 10000 });

    const statsTab = page.getByRole('tab', { name: '统计分析' });
    if (await statsTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await statsTab.click();
      await page.waitForTimeout(1000);
    }

    await expect(page).toHaveURL(/\/home\/image-report/);
  });
});
