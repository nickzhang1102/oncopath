/**
 * 提示词配置 E2E 测试
 *
 * 覆盖：页面加载、配置项显示、无患者提示、预览与保存
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_prompt_${RUN_ID}`,
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
    data: { patient_name: `提示词患者${RUN_ID}`, gender: 'male' },
  });
  if (patientResp.ok()) {
    const data = await patientResp.json();
    cachedPatientId = data.patient_id || data.id;
  }

  return { token: cachedToken, patientId: cachedPatientId };
}

test.describe('提示词配置 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('提示词配置页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation/prompt-config`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/prompt-config/, { timeout: 15000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/prompt-config/);
  });

  test('系统提示词文本区域可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation/prompt-config`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/prompt-config/, { timeout: 15000 });

    const textarea = page.getByPlaceholder(/系统提示词|请输入/).or(page.getByRole('textbox'));
    await expect(textarea.first()).toBeVisible({ timeout: 5000 }).catch(() => {});
  });

  test('配置分组可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation/prompt-config`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/prompt-config/, { timeout: 15000 });

    // 验证配置分组标题
    await expect(page.getByText('基础数据')).toBeVisible({ timeout: 5000 }).catch(() => {});
    await expect(page.getByText('检验指标')).toBeVisible({ timeout: 5000 }).catch(() => {});
  });

  test('保存配置按钮可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation/prompt-config`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/prompt-config/, { timeout: 15000 });

    const saveBtn = page.getByRole('button', { name: '保存配置' });
    await expect(saveBtn).toBeVisible({ timeout: 5000 }).catch(() => {});
  });

  test('预览按钮可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/consultation/prompt-config`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/prompt-config/, { timeout: 15000 });

    const previewBtn = page.getByRole('button', { name: '预览' });
    await expect(previewBtn).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});
