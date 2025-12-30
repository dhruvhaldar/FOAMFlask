
import { test, expect } from '@playwright/test';

test.describe('Layout & Responsiveness', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('/api/startup_status', async route => {
      await route.fulfill({ json: { status: 'completed', message: 'Ready' } });
    });
    await page.goto('/');
    await expect(page.locator('#startup-modal')).toBeHidden();
  });

  test('should have main content area', async ({ page }) => {
    await expect(page.locator('#main-content')).toBeVisible();
    // Output is on Run tab, so switch to it
    await page.click('#nav-run');
    await expect(page.locator('#output')).toBeVisible();
  });

  test('should adjust to mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    // Check if navigation is still accessible (maybe it stacks?)
    const nav = page.locator('nav');
    await expect(nav).toBeVisible();

    // Verify buttons don't overflow (basic check)
    const setupBtn = page.locator('#nav-setup');
    await expect(setupBtn).toBeVisible();
  });

  test('should show notification container fixed', async ({ page }) => {
    // Check CSS properties of notification container
    const container = page.locator('#notificationContainer');
    await expect(container).toHaveCSS('position', 'fixed');
    await expect(container).toHaveCSS('pointer-events', 'none');
  });
});
