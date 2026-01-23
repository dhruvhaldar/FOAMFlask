
import { test, expect } from '@playwright/test';

test.describe('Log Performance', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('/api/startup_status', async route => {
      await route.fulfill({ json: { status: 'completed', message: 'Ready' } });
    });
    await page.goto('/');
    await expect(page.locator('#startup-modal')).toBeHidden();

    // Switch to Run tab to see output
    await page.click('#nav-run');
    await expect(page.locator('#output')).toBeVisible();
  });

  test('should limit DOM nodes in log output', async ({ page }) => {
    // Mock the /run endpoint to stream many lines
    await page.route('/run', async route => {
      // Simulate a stream by returning a large body
      // We use <div> format to match our target optimization,
      // but even with <br> (current state), we want to test if it grows unbounded.
      // Wait, current state is <br>.
      // If we simply check character length or just line count?
      // With <br>, line count is harder to verify via selectors.
      // But we can check innerHTML length.

      const lines = Array.from({ length: 5000 }, (_, i) => `<div>Line ${i}</div>`).join('');

      await route.fulfill({
          status: 200,
          contentType: 'text/html',
          body: lines
      });
    });

    // We need to override the window.runCommand or simulate the fetch trigger
    // Since runCommand is exposed on window, we can call it.
    await page.evaluate(async () => {
        // We need a dummy button
        const btn = document.createElement('button');
        // We also need caseDir and tutorial selected or passed?
        // runCommand uses global caseDir and document.getElementById("tutorialSelect")

        // Mock getElementById for tutorialSelect if needed, or just set it
        // The page setup might already have it.
        // We can just call the fetch directly? No, we want to test the frontend processing loop.

        // Let's set the global variables if needed.
        // runCommand checks tutorialSelect value.
        const select = document.getElementById("tutorialSelect") as HTMLSelectElement;
        if (select && select.options.length > 0) select.selectedIndex = 0;
        else if (select) {
            const opt = document.createElement("option");
            opt.value = "mock/tutorial";
            opt.selected = true;
            select.appendChild(opt);
        }

        await window.runCommand('test_cmd', btn);
    });

    // Wait for log to populate
    await expect(page.locator('#output')).toContainText('Line 4999');

    // Check child count
    // NOTE: This test assumes we switch to <div> format.
    // If we run this test against current code (with <br>), childElementCount might be 0 (text nodes + brs?).
    // <br> is an Element.
    // So 5000 lines = 5000 divs OR 5000 <br>s + text nodes.
    // So childElementCount should be 5000 either way.

    const count = await page.locator('#output > *').count();
    console.log(`Log child count: ${count}`);

    // Expectation: Without optimization, count is 5000.
    // With optimization, it should be capped (e.g. 2500).
    // We assert <= 2500 (plus a small buffer if implementation varies, but exact <= 2500 is expected).
    expect(count).toBeLessThanOrEqual(2500);
  });
});
