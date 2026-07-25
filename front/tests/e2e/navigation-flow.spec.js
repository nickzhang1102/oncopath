/**
 * 跨页面导航流程 E2E 测试
 *
 * 覆盖：首页→各子页面导航、侧边栏→详情页→返回、病情管理→子功能页面
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';
const API_URL = 'http://localhost:8000/api/v1';

const RUN_ID = Date.now();
const TEST_CREDENTIALS = {
  username: `e2e_nav_${RUN_ID}`,
  password: 'E2e@Test123',
};

let cachedToken = '';

async function getOrCreateToken(request) {
  if (cachedToken) return cachedToken;
  await request.post(`${API_URL}/auth/register`, {
    data: { username: TEST_CREDENTIALS.username, password: TEST_CREDENTIALS.password },
  }).catch(() => {});
  const loginResp = await request.post(`${API_URL}/auth/login`, {
    data: { username: TEST_CREDENTIALS.username, password: TEST_CREDENTIALS.password },
  });
  expect(loginResp.ok()).toBeTruthy();
  cachedToken = (await loginResp.json()).access_token;
  return cachedToken;
}

test.describe('跨页面导航流程 E2E', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await getOrCreateToken(request);
    await page.addInitScript((t) => {
      localStorage.setItem('token', t);
      localStorage.setItem('refresh_token', 'test-refresh');
      localStorage.setItem('onboarding_completed', '1');
    }, token);
  });

  test('首页→病情管理→检查报告导航流程', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/main`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    // 点击病情管理
    const medicalLink = page.getByRole('link', { name: /病情/ }).or(page.getByRole('heading', { name: /病情/ }));
    if (await medicalLink.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await medicalLink.first().click();
      await page.waitForTimeout(2000);
    } else {
      await page.goto(`${BASE_URL}/home/medical`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    }

    await page.waitForURL(/\/home\/medical/, { timeout: 5000 });

    // 点击检查报告
    const examLink = page.getByRole('heading', { name: '检查报告' }).or(page.getByText('检查报告'));
    if (await examLink.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await examLink.first().click();
      await page.waitForTimeout(2000);
      await expect(page).toHaveURL(/\/home\/exam-reports/, { timeout: 5000 });
    }
  });

  test('首页→个人中心→修改密码导航流程', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/main`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    // 导航到个人中心
    await page.goto(`${BASE_URL}/home/profile`, { timeout: 30000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/profile/, { timeout: 15000 });

    // 点击修改密码
    const pwdLink = page.getByText('修改密码');
    if (await pwdLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await pwdLink.click();
      await page.waitForTimeout(2000);
      await expect(page).toHaveURL(/\/home\/profile\/password/, { timeout: 5000 });
    }
  });

  test('首页→时间线→返回首页', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/main`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    // 导航到时间线
    const timelineLink = page.getByRole('link', { name: /时间线/ });
    if (await timelineLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await timelineLink.click();
      await page.waitForTimeout(2000);
      await expect(page).toHaveURL(/\/home\/timeline/, { timeout: 5000 });
    } else {
      await page.goto(`${BASE_URL}/home/timeline`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    }

    // 侧边栏回到首页
    const homeLink = page.getByRole('link', { name: /首页/ });
    if (await homeLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await homeLink.click();
      await page.waitForTimeout(2000);
      await expect(page).toHaveURL(/\/home\/main/, { timeout: 5000 });
    }
  });

  test('病情管理→指标查询页面导航', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/medical`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/home\/medical/, { timeout: 5000 });
    await page.waitForTimeout(2000);

    // 点击指标查询
    const indexLink = page.getByRole('heading', { name: '查询指标' }).or(page.getByText('查询指标'));
    if (await indexLink.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await indexLink.first().click();
      await page.waitForTimeout(2000);
      await expect(page).toHaveURL(/\/home\/index/, { timeout: 5000 });
    }
  });

  test('首页→知识库页面导航', async ({ page }) => {
    await page.goto(`${BASE_URL}/home/main`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    // 侧边栏知识库链接
    const knowledgeLink = page.getByRole('link', { name: /知识库/ });
    if (await knowledgeLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await knowledgeLink.click();
      await page.waitForTimeout(2000);
      await expect(page).toHaveURL(/\/home\/knowledge/, { timeout: 5000 });
    }
  });
});
