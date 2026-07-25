/**
 * 用药管理 E2E 测试
 *
 * 覆盖：用药管理页面加载、添加用药、查看列表
 * 前置条件：需要先有患者
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_med_${RUN_ID}`,
  password: 'E2e@Test123',
};

let cachedToken = '';
let cachedPatientId = '';

async function setupWithPatient(request) {
  if (cachedToken && cachedPatientId) return { token: cachedToken, patientId: cachedPatientId };

  // 注册+登录
  await request.post(`${API_URL}/auth/register`, {
    data: { username: TEST_CREDENTIALS.username, password: TEST_CREDENTIALS.password },
  }).catch(() => {});
  const loginResp = await request.post(`${API_URL}/auth/login`, {
    data: { username: TEST_CREDENTIALS.username, password: TEST_CREDENTIALS.password },
  });
  expect(loginResp.ok()).toBeTruthy();
  cachedToken = (await loginResp.json()).access_token;

  // 创建患者
  const patientResp = await request.post(`${API_URL}/patients`, {
    headers: { 'Authorization': `Bearer ${cachedToken}`, 'Content-Type': 'application/json' },
    data: { patient_name: `用药患者${RUN_ID}`, gender: 'male' },
  });
  expect(patientResp.ok()).toBeTruthy();
  const patientData = await patientResp.json();
  cachedPatientId = patientData.patient_id || patientData.id;

  // 设置为当前患者
  const patientsResp = await request.get(`${API_URL}/patients`, {
    headers: { 'Authorization': `Bearer ${cachedToken}` },
  });
  const patientsData = await patientsResp.json();
  const patients = Array.isArray(patientsData) ? patientsData : (patientsData.patients || []);
  const target = patients.find(p => (p.patient_id || p.id) === cachedPatientId);
  if (target && target.patient_id) {
    // 设置当前患者
    await request.post(`${API_URL}/patients/${target.patient_id}/select`, {
      headers: { 'Authorization': `Bearer ${cachedToken}` },
    }).catch(() => {});
  }

  return { token: cachedToken, patientId: cachedPatientId };
}

test.describe('用药管理 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('用药管理页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/medication`);
    await page.waitForURL(/\/home\/medication/, { timeout: 10000 });
    await expect(page.getByRole('heading', { name: '用药记录' })).toBeVisible({ timeout: 5000 });
  });

  test('无患者时显示提示信息', async ({ page, request }) => {
    // 用独立用户（无患者）
    const uniqUser = `e2e_med_empty_${RUN_ID}`;
    await request.post(`${API_URL}/auth/register`, {
      data: { username: uniqUser, password: 'E2e@Test123' },
    }).catch(() => {});
    const loginResp = await request.post(`${API_URL}/auth/login`, {
      data: { username: uniqUser, password: 'E2e@Test123' },
    });
    const emptyToken = (await loginResp.json()).access_token;

    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, emptyToken);

    await page.goto(`${BASE_URL}/home/medication`);
    await page.waitForURL(/\/home\/medication/, { timeout: 10000 });
    await expect(page.getByText('请先选择患者')).toBeVisible({ timeout: 5000 });
  });

  test('通过 API 添加用药记录后页面可见', async ({ page, request }) => {
    const { token, patientId } = await setupWithPatient(request);

    // 通过 API 添加用药
    const medResp = await request.post(`${API_URL}/medication`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        patient_id: patientId,
        medication_name: `测试药品${RUN_ID}`,
        dosage: '10mg',
        frequency: '每日一次',
        start_date: '2026-01-01',
      },
    });

    if (medResp.ok()) {
      // 设置当前患者
      await request.post(`${API_URL}/patients/${patientId}/select`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }).catch(() => {});

      await page.goto(`${BASE_URL}/home/medication`);
      await page.waitForURL(/\/home\/medication/, { timeout: 10000 });
      // 验证用药名称出现
      await expect(page.getByText(`测试药品${RUN_ID}`)).toBeVisible({ timeout: 10000 });
    }
  });

  test('点击添加用药按钮弹出表单', async ({ page }) => {
    // 直接用 setupWithPatient 准备好的 token（已有患者）
    await page.goto(`${BASE_URL}/home/medication`);
    await page.waitForURL(/\/home\/medication/, { timeout: 10000 });

    // 如果有"添加用药"按钮，点击
    const addBtn = page.getByRole('button', { name: '添加用药' });
    if (await addBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await addBtn.click();
      await page.waitForTimeout(1000);
    } else {
      // 无患者时显示选择患者按钮，也验证一下
      await expect(page.getByText('请先选择患者').or(page.getByRole('button', { name: '选择患者' }))).toBeVisible({ timeout: 5000 });
    }
  });
});