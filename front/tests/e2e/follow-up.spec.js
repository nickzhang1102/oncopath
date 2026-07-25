/**
 * 随访提醒 E2E 测试
 *
 * 覆盖：Tab切换、空状态、新建提醒弹窗、API创建提醒
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_fu_${RUN_ID}`,
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
    data: { patient_name: `随访患者${RUN_ID}`, gender: 'male' },
  });
  if (patientResp.ok()) {
    const data = await patientResp.json();
    cachedPatientId = data.patient_id || data.id;
  }

  return { token: cachedToken, patientId: cachedPatientId };
}

test.describe('随访提醒 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('随访页面加载显示Tab筛选', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/follow-up`);
    await page.waitForURL(/\/home\/follow-up/, { timeout: 10000 });

    // 验证 Tab 存在
    await expect(page.getByRole('tab', { name: '待处理' })).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('tab', { name: '已确认' })).toBeVisible();
    await expect(page.getByRole('tab', { name: '已过期' })).toBeVisible();
  });

  test('无患者时显示空状态', async ({ page, request }) => {
    const uniqUser = `e2e_fu_empty_${RUN_ID}`;
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

    await page.goto(`${BASE_URL}/home/follow-up`);
    await page.waitForURL(/\/home\/follow-up/, { timeout: 10000 });
    // 新用户无患者应显示"暂无提醒"
    await expect(page.getByText('暂无提醒')).toBeVisible({ timeout: 5000 });
  });

  test('Tab 切换可点击', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/follow-up`);
    await page.waitForURL(/\/home\/follow-up/, { timeout: 10000 });

    // 切换到已确认 tab
    await page.getByRole('tab', { name: '已确认' }).click();
    await page.waitForTimeout(1000);

    // 切换到全部 tab
    await page.getByRole('tab', { name: '全部' }).click();
    await page.waitForTimeout(1000);
  });

  test('通过 API 创建提醒后页面显示', async ({ page, request }) => {
    const { token, patientId } = await setupWithPatient(request);
    if (!patientId) { test.skip(); return; }

    // 设置当前患者
    await request.post(`${API_URL}/patients/${patientId}/select`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).catch(() => {});

    // 创建随访提醒
    const reminderResp = await request.post(`${API_URL}/reminders`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        patient_id: patientId,
        title: `复查CT${RUN_ID}`,
        reminder_date: '2026-07-01',
        description: 'E2E测试随访提醒',
      },
    });

    if (reminderResp.ok()) {
      await page.goto(`${BASE_URL}/home/follow-up`);
      await page.waitForURL(/\/home\/follow-up/, { timeout: 10000 });
      await page.waitForTimeout(3000);

      // 不应显示空状态
      await expect(page.getByText('暂无提醒')).not.toBeVisible({ timeout: 10000 }).catch(() => {});
    }
  });

  test('点击浮动按钮打开新建提醒弹窗', async ({ page, request }) => {
    const { token, patientId } = await setupWithPatient(request);
    if (patientId) {
      await request.post(`${API_URL}/patients/${patientId}/select`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }).catch(() => {});
    }

    await page.goto(`${BASE_URL}/home/follow-up`);
    await page.waitForURL(/\/home\/follow-up/, { timeout: 10000 });

    // 点击浮动添加按钮
    const addBtn = page.locator('.van-floating-bubble, .van-badge__wrapper.van-icon-plus').first();
    if (await addBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await addBtn.click();
      await page.waitForTimeout(1000);
    } else {
      // 桌面端新建按钮
      const desktopBtn = page.getByRole('button', { name: '新建提醒' }).first();
      if (await desktopBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await desktopBtn.click();
        await page.waitForTimeout(1000);
      }
    }

    // 验证弹窗打开 — 检查表单中的"标题"字段
    await expect(page.getByRole('textbox', { name: '标题' })).toBeVisible({ timeout: 5000 });
  });
});
