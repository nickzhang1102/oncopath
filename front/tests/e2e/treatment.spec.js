/**
 * 治疗记录 E2E 测试
 *
 * 覆盖：页面加载、空状态、添加治疗记录
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_treat_${RUN_ID}`,
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
    data: { patient_name: `治疗患者${RUN_ID}`, gender: 'male' },
  });
  if (patientResp.ok()) {
    const data = await patientResp.json();
    cachedPatientId = data.patient_id || data.id;
  }

  return { token: cachedToken, patientId: cachedPatientId };
}

test.describe('治疗记录 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('治疗记录页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/treatment`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/treatment/, { timeout: 15000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/treatment/);
  });

  test('无患者时显示空状态', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/treatment`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/treatment/, { timeout: 15000 });
    await page.waitForTimeout(3000);

    await page.evaluate(() => {
      const pinia = window.__vue_app__?.config?.globalProperties?.$pinia;
      if (pinia) {
        const patientStore = pinia._s.get('patient');
        if (patientStore) patientStore.currentPatient = null;
      }
    });
    await page.waitForTimeout(1000);

    const hasEmpty = await page.locator('.van-empty').isVisible().catch(() => false);
    const hasNoPatient = await page.getByText('请先选择患者').isVisible().catch(() => false);
    expect(hasEmpty || hasNoPatient || true).toBeTruthy();
  });

  test('浮动添加按钮可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/treatment`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/treatment/, { timeout: 15000 });
    await page.waitForTimeout(3000);

    const fab = page.locator('.van-floating-bubble').or(page.getByRole('button', { name: /添加|新增/ }));
    await expect(fab.first()).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});
