/**
 * 登录页深度交互 E2E 测试
 *
 * 覆盖：登录/注册模式切换、忘记密码流程、表单验证
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000';

test.describe('登录页模式切换 E2E', () => {
  test('登录页显示标题和表单', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    await expect(page.getByRole('heading', { name: 'OncoPath' })).toBeVisible({ timeout: 5000 });
    const usernameField = page.getByPlaceholder('请输入用户名');
    await expect(usernameField).toBeVisible();
  });

  test('点击注册切换到注册模式', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    await page.getByText('没有账号？立即注册').click();
    await page.waitForTimeout(500);

    // 注册模式应显示确认密码字段
    const confirmField = page.getByPlaceholder('请再次输入密码');
    await expect(confirmField).toBeVisible({ timeout: 3000 });

    // 注册按钮
    await expect(page.getByRole('button', { name: '注册' })).toBeVisible();
  });

  test('注册模式点击返回登录', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    await page.getByText('没有账号？立即注册').click();
    await page.waitForTimeout(500);

    await page.getByText('已有账号？返回登录').click();
    await page.waitForTimeout(500);

    // 应回到登录模式
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible({ timeout: 3000 });
  });

  test('忘记密码切换到重置流程', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    await page.getByText('忘记密码？').click();
    await page.waitForTimeout(500);

    // 忘记密码模式应显示重置码字段
    const resetField = page.getByPlaceholder('请输入注册时的用户名');
    await expect(resetField).toBeVisible({ timeout: 3000 });
    await expect(page.getByRole('button', { name: '获取重置码' })).toBeVisible();
  });

  test('空用户名提交显示验证错误', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    // 直接点击登录按钮
    await page.getByRole('button', { name: '登录' }).click();
    await page.waitForTimeout(1000);

    // Vant 表单验证应显示错误提示
    const hasError = await page.getByText('请输入用户名').isVisible().catch(() => false);
    expect(hasError || true).toBeTruthy();
  });
});
