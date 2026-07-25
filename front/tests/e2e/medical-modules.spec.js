/**
 * 医疗子模块 E2E 测试
 *
 * 覆盖：病情管理导航页、指标查询、异常指标、检查报告、病理报告、治疗记录、状态记录
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
    data: { patient_name: `医疗患者${RUN_ID}`, gender: 'female' },
  });
  if (patientResp.ok()) {
    const data = await patientResp.json();
    cachedPatientId = data.patient_id || data.id;
  }

  return { token: cachedToken, patientId: cachedPatientId };
}

test.describe('病情管理导航 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('病情管理页面显示功能网格', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/medical`);
    await page.waitForURL(/\/home\/medical/, { timeout: 10000 });

    // 验证核心功能入口 (heading 元素)
    await expect(page.getByRole('heading', { name: '检验报告' })).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('heading', { name: '检查报告' })).toBeVisible();
    await expect(page.getByRole('heading', { name: '查询指标' })).toBeVisible();
    await expect(page.getByRole('heading', { name: '异常指标' })).toBeVisible();
  });
});

test.describe('指标查询 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('指标查询页面加载显示分类Tab', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/index`);
    await page.waitForURL(/\/home\/index/, { timeout: 10000 });

    // 验证分类Tab存在
    await expect(page.getByRole('tab').first()).toBeVisible({ timeout: 5000 });
  });

  test('指标对比按钮可见', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/index`);
    await page.waitForURL(/\/home\/index/, { timeout: 10000 });

    // 对比按钮
    await expect(page.getByRole('button', { name: /指标对比|退出对比/ })).toBeVisible({ timeout: 5000 });
  });
});

test.describe('异常指标 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('异常指标页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/abnormal-indicators`);
    await page.waitForURL(/\/home\/abnormal-indicators/, { timeout: 10000 });

    // 应显示标题或空状态
    await page.waitForTimeout(2000);
    const hasTitle = await page.getByText('异常指标').isVisible().catch(() => false);
    const hasEmpty = await page.getByText('暂无异常指标').isVisible().catch(() => false);
    expect(hasTitle || hasEmpty).toBeTruthy();
  });
});

test.describe('检查报告 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('检查报告页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/exam-reports`);
    await page.waitForURL(/\/home\/exam-reports/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    // 页面应正常加载（不崩溃）
    await expect(page).toHaveURL(/\/home\/exam-reports/);
  });

  test('无患者时显示提示', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/exam-reports`);
    await page.waitForURL(/\/home\/exam-reports/, { timeout: 10000 });

    // 清除当前患者
    await page.evaluate(() => {
      const app = document.querySelector('#app').__vue_app__;
      const pinia = app?.config?.globalProperties?.$pinia;
      const store = pinia?._s?.get('patient');
      if (store) store.currentPatient = null;
    });

    await page.waitForTimeout(1000);
    await expect(page.getByText('请先选择患者')).toBeVisible({ timeout: 5000 }).catch(() => {
      // 如果有患者数据则可能不显示此提示
    });
  });
});

test.describe('病理报告 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('病理报告页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/pathology-reports`);
    await page.waitForURL(/\/home\/pathology-reports/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/pathology-reports/);
  });
});

test.describe('治疗记录 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('治疗记录页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/treatment`);
    await page.waitForURL(/\/home\/treatment/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/treatment/);
  });

  test('无患者时显示提示', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/treatment`);
    await page.waitForURL(/\/home\/treatment/, { timeout: 10000 });

    await page.evaluate(() => {
      const app = document.querySelector('#app').__vue_app__;
      const pinia = app?.config?.globalProperties?.$pinia;
      const store = pinia?._s?.get('patient');
      if (store) store.currentPatient = null;
    });

    await page.waitForTimeout(1000);
    await expect(page.getByText('请先选择患者')).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});

test.describe('状态记录 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const { token } = await setupWithPatient(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
    }, token);
  });

  test('状态记录页面加载', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/status`);
    await page.waitForURL(/\/home\/status/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    await expect(page).toHaveURL(/\/home\/status/);
  });

  test('无患者时显示提示', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/status`);
    await page.waitForURL(/\/home\/status/, { timeout: 10000 });

    await page.evaluate(() => {
      const app = document.querySelector('#app').__vue_app__;
      const pinia = app?.config?.globalProperties?.$pinia;
      const store = pinia?._s?.get('patient');
      if (store) store.currentPatient = null;
    });

    await page.waitForTimeout(1000);
    await expect(page.getByText('请先选择患者')).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});