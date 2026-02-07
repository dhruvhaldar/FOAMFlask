import { test, expect } from '@playwright/test';

test.describe('Post Processing View', () => {
  test.beforeEach(async ({ page }) => {
    // Mock startup status
    await page.route('/api/startup_status', async route => {
      await route.fulfill({ json: { status: 'completed', message: 'Ready' } });
    });

    // Navigate to the app (assuming it's running)
    // We can mock the backend responses if needed, but for layout verification, we just need the frontend
    await page.goto('/');

    // Force remove modal if it persists (safety net)
    await page.evaluate(() => {
        const modal = document.getElementById('startup-modal');
        if (modal) modal.remove();
    });

    // Set active case to bypass "No Active Case" screen
    await page.evaluate(() => {
        (window as any).selectCase('test_case');
    });

    // Switch to Post page
    await page.click('#nav-post');
    await expect(page.locator('#page-post')).toBeVisible();
  });

  test('should show landing view by default', async ({ page }) => {
    await expect(page.locator('#post-landing-view')).toBeVisible();
    await expect(page.locator('#post-contour-view')).toBeHidden();
  });

  test('should display feature cards in landing view', async ({ page }) => {
    const landing = page.locator('#post-landing-view');

    // Check for 4 cards (1 active + 3 disabled)
    await expect(landing.locator('.glass-panel')).toHaveCount(4);

    // Check Contour Card
    const contourCard = landing.locator('button', { hasText: 'Contour' });
    await expect(contourCard).toBeVisible();
    await expect(contourCard).toBeEnabled();

    // Check Slice Card (Placeholder)
    const sliceCard = landing.locator('div', { hasText: 'Slice' }).filter({ hasText: 'Soon' });
    await expect(sliceCard).toBeVisible();

    // Check Streamline Card (Placeholder)
    const streamlineCard = landing.locator('div', { hasText: 'Streamline' }).filter({ hasText: 'Soon' });
    await expect(streamlineCard).toBeVisible();

    // Check Surface Projection Card (Placeholder)
    const surfaceCard = landing.locator('div', { hasText: 'Surface Projection' }).filter({ hasText: 'Soon' });
    await expect(surfaceCard).toBeVisible();
  });

  test('should navigate to contour view and back', async ({ page }) => {
    // Click Contour Card
    await page.click('#card-contour');

    // Verify View Switch
    await expect(page.locator('#post-landing-view')).toBeHidden();
    await expect(page.locator('#post-contour-view')).toBeVisible();

    // Verify Back Button exists
    const backBtn = page.locator('#post-contour-view button[aria-label="Back to selection"]');
    await expect(backBtn).toBeVisible();

    // Click Back Button
    await backBtn.click();

    // Verify View Switch Back
    await expect(page.locator('#post-landing-view')).toBeVisible();
    await expect(page.locator('#post-contour-view')).toBeHidden();
  });

  test('should look correct (screenshot)', async ({ page }) => {
    // wait for landing view to be stable
    await page.waitForSelector('#post-landing-view');

    // Take screenshot
    await page.screenshot({ path: 'post_processing_landing.png', fullPage: true });
  });
});
