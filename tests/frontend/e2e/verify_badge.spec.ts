import { test, expect } from '@playwright/test';

test.describe('Active Case Badge', () => {
  test('should display active case in badge when selected', async ({ page }) => {
    // Navigate to the app (assuming mock app is running on localhost:5000)
    // Note: This requires mock_app.py to be running.
    await page.goto('http://localhost:5000');

    // Wait for startup modal to disappear if present
    const modal = page.locator('#startup-modal');
    if (await modal.isVisible()) {
        await modal.waitFor({ state: 'hidden', timeout: 10000 });
    }

    // Wait for the case select to be populated (mock app returns case1, case2)
    const caseSelect = page.locator('#caseSelect');
    await expect(caseSelect).toBeVisible();

    // Sometimes it takes a moment for fetch to complete and populate options
    await expect(caseSelect.locator('option[value="case1"]')).toBeAttached();

    // Select a case
    await caseSelect.selectOption('case1');

    // Verify badge visibility and text
    const badge = page.locator('#activeCaseBadge');
    await expect(badge).toBeVisible();
    await expect(badge).toHaveText('case1');

    // Verify restoration on reload
    await page.reload();
    // Wait for modal again just in case
    if (await modal.isVisible()) {
        await modal.waitFor({ state: 'hidden', timeout: 10000 });
    }

    await expect(badge).toBeVisible();
    await expect(badge).toHaveText('case1');
  });
});
