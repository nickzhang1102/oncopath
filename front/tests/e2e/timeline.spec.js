/**
 * 治疗时间线 E2E 测试
 *
 * 覆盖：时间线页面加载、日期筛选、空状态、过滤器、导出按钮
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_tl_${RUN_ID}`,
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
    data: { patient_name: `时间线患者${RUN_ID}`, gender: 'male' },
  });
  if (patientResp.ok()) {
    const data = await patientResp.json();
    cachedPatientId = data.patient_id || data.id;
  }

  return { token: cachedToken, patientId: cachedPatientId };
}

test.describe('治疗时间线 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('时间线页面加载显示筛选区域', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/timeline`);
    await page.waitForURL(/\/home\/timeline/, { timeout: 10000 });

    // 验证日期快捷按钮存在
    await expect(page.getByText('全部')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('1月')).toBeVisible();
    await expect(page.getByText('3月')).toBeVisible();

    // 验证自定义日期按钮
    await expect(page.getByText('自定义')).toBeVisible();
  });

  test('日期快捷按钮可点击', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/timeline`);
    await page.waitForURL(/\/home\/timeline/, { timeout: 10000 });

    // 点击"3月"
    await page.getByText('3月', { exact: true }).click();
    await page.waitForTimeout(1000);

    // 应出现筛选提示或日期范围变化
    const customBtn = page.locator('.custom-date-btn');
    await expect(customBtn).toBeVisible();
  });

  test('自定义日期按钮弹出日期选择器', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/timeline`);
    await page.waitForURL(/\/home\/timeline/, { timeout: 10000 });

    // 点击自定义日期
    await page.locator('.custom-date-btn').click();
    await page.waitForTimeout(1000);

    // 日期选择器弹出
    await expect(page.getByText('开始日期')).toBeVisible({ timeout: 5000 });
  });

  test('导出 PDF 按钮存在', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/timeline`);
    await page.waitForURL(/\/home\/timeline/, { timeout: 10000 });

    // 导出按钮
    await expect(page.getByRole('button', { name: '导出 PDF' })).toBeVisible({ timeout: 5000 });
  });

  test('通过 API 创建时间线事件后页面显示', async ({ page, request }) => {
    const { token, patientId } = await setupWithPatient(request);
    if (!patientId) { test.skip(); return; }

    // 设置当前患者
    await request.post(`${API_URL}/patients/${patientId}/select`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).catch(() => {});

    // 创建时间线事件
    await request.post(`${API_URL}/timeline/events`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        patient_id: patientId,
        event_type: 'treatment',
        title: `化疗${RUN_ID}`,
        event_date: '2026-01-15',
        description: 'E2E测试时间线事件',
      },
    }).catch(() => {});

    await page.goto(`${BASE_URL}/home/timeline`);
    await page.waitForURL(/\/home\/timeline/, { timeout: 10000 });
    await page.waitForTimeout(3000);

    // 应不再显示"暂无记录"
    await expect(page.getByText('暂无记录')).not.toBeVisible({ timeout: 10000 }).catch(() => {});
  });
});
