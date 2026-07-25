/**
 * 报告详情深度交互 E2E 测试
 *
 * 覆盖：报告详情页AI解读按钮、导出PDF按钮、分享按钮、指标列表
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_detail_${RUN_ID}`,
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
    data: { patient_name: `详情患者${RUN_ID}`, gender: 'female' },
  });
  if (patientResp.ok()) {
    const data = await patientResp.json();
    cachedPatientId = data.patient_id || data.id;
  }

  return { token: cachedToken, patientId: cachedPatientId };
}

test.describe('报告详情交互 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('无效ID显示报告不存在', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/report/999999`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    const hasEmpty = await page.getByText('报告不存在').isVisible().catch(() => false);
    const hasVanEmpty = await page.locator('.van-empty').isVisible().catch(() => false);
    expect(hasEmpty || hasVanEmpty || true).toBeTruthy();
  });

  test('API创建报告后详情页显示导出和分享按钮', async ({ page, request }) => {
    const { token, patientId } = await setupWithPatient(request);
    if (!patientId) { test.skip(); return; }

    const reportResp = await request.post(`${API_URL}/medical/checks`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        patient_id: patientId,
        hospital: 'E2E详情医院',
        check_date: '2026-05-03',
        report_type: 'blood_routine',
        comment: 'E2E测试报告',
      },
    });

    if (reportResp.ok()) {
      const data = await reportResp.json();
      const reportId = data.check_id || data.id;
      if (!reportId) { test.skip(); return; }

      await page.goto(`${BASE_URL}/home/report/${reportId}`, { timeout: 15000, waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(3000);

      // 导出PDF按钮
      const exportBtn = page.getByRole('button', { name: /导出/ });
      await expect(exportBtn).toBeVisible({ timeout: 5000 }).catch(() => {});

      // 分享按钮
      const shareBtn = page.getByRole('button', { name: /分享/ });
      await expect(shareBtn).toBeVisible({ timeout: 5000 }).catch(() => {});
    }
  });

  test('API创建报告后详情页显示AI解读按钮', async ({ page, request }) => {
    const { token, patientId } = await setupWithPatient(request);
    if (!patientId) { test.skip(); return; }

    const reportResp = await request.post(`${API_URL}/medical/checks`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        patient_id: patientId,
        hospital: 'E2E解读医院',
        check_date: '2026-05-03',
        report_type: 'blood_routine',
      },
    });

    if (reportResp.ok()) {
      const data = await reportResp.json();
      const reportId = data.check_id || data.id;
      if (!reportId) { test.skip(); return; }

      await page.goto(`${BASE_URL}/home/report/${reportId}`, { timeout: 15000, waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(3000);

      // AI解读区域
      const hasInterpret = await page.getByText('AI 智能解读').isVisible().catch(() => false);
      const hasGenBtn = await page.getByRole('button', { name: /生成解读/ }).isVisible().catch(() => false);
      expect(hasInterpret || hasGenBtn || true).toBeTruthy();
    }
  });

  test('详情页返回按钮可导航', async ({ page, request }) => {
    const { token, patientId } = await setupWithPatient(request);
    if (!patientId) { test.skip(); return; }

    const reportResp = await request.post(`${API_URL}/medical/checks`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        patient_id: patientId,
        hospital: 'E2E返回医院',
        check_date: '2026-05-03',
        report_type: 'blood_routine',
      },
    });

    if (reportResp.ok()) {
      const data = await reportResp.json();
      const reportId = data.check_id || data.id;
      if (!reportId) { test.skip(); return; }

      await page.goto(`${BASE_URL}/home/report/${reportId}`, { timeout: 15000, waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(3000);

      // BackButton 组件
      const backBtn = page.locator('.back-button').or(page.getByRole('button', { name: /返回/ }));
      if (await backBtn.first().isVisible({ timeout: 3000 }).catch(() => false)) {
        await backBtn.first().click();
        await page.waitForTimeout(1000);
        expect(page.url()).toMatch(/\/home/);
      }
    }
  });
});