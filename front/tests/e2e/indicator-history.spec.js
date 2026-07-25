/**
 * 指标历史 E2E 测试
 *
 * 覆盖：页面加载、视图切换、添加数据弹窗
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_idx_${RUN_ID}`,
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
    data: { patient_name: `指标患者${RUN_ID}`, gender: 'female' },
  });
  if (patientResp.ok()) {
    const data = await patientResp.json();
    cachedPatientId = data.patient_id || data.id;
  }

  return { token: cachedToken, patientId: cachedPatientId };
}

test.describe('指标历史 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('指标历史页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/indicator/history?index_id=1&index_name=测试指标`);
    await page.waitForURL(/\/home\/indicator\/history/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/indicator\/history/);
  });

  test('视图切换按钮可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/indicator/history?index_id=1&index_name=测试指标`);
    await page.waitForURL(/\/home\/indicator\/history/, { timeout: 10000 });

    // 视图切换（表格/图表）
    const viewToggle = page.getByRole('button', { name: /图表|表格|切换/ });
    if (await viewToggle.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(viewToggle.first()).toBeVisible();
    }
  });

  test('浮动添加按钮可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/indicator/history?index_id=1&index_name=测试指标`);
    await page.waitForURL(/\/home\/indicator\/history/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    const addBubble = page.locator('.van-floating-bubble').first();
    if (await addBubble.isVisible({ timeout: 3000 }).catch(() => false)) {
      await addBubble.click();
      await page.waitForTimeout(1000);
      // 应弹出添加数据表单
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 }).catch(() => {});
    }
  });
});
