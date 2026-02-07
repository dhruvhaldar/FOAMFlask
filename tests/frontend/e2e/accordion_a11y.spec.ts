
import { test, expect } from '@playwright/test';

test.describe('Accordion Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    // Mock startup status to remove modal
    await page.route('/api/startup_status', async route => {
      await route.fulfill({ json: { status: 'completed', message: 'Ready' } });
    });

    // Mock basic API responses to avoid errors
    await page.route('/get_case_root', async route => route.fulfill({ json: { caseDir: '/tmp/test' } }));
    await page.route('/get_docker_config', async route => route.fulfill({ json: { dockerImage: 'img', openfoamVersion: 'v1' } }));
    await page.route('/api/cases/list', async route => route.fulfill({ json: { cases: ['case1'] } }));
    // Mock available meshes to avoid errors when refreshing lists
    await page.route('/api/available_meshes?tutorial=case1', async route => route.fulfill({ json: { meshes: [] } }));

    await page.goto('/');

    // Force remove modal if it persists (safety net)
    await page.evaluate(() => {
        const modal = document.getElementById('startup-modal');
        if (modal) modal.remove();
    });

    // Set active case to bypass "No Active Case" screen
    await page.evaluate(() => {
        (window as any).selectCase('case1');
    });

    // Navigate to Post Processing
    await page.click('#nav-post');
    await expect(page.locator('#page-post')).toBeVisible();
  });

  test('Load Custom VTK File accordion functions correctly', async ({ page }) => {
    // 1. Enter Contour View (where the accordion is)
    await page.click('#card-contour');
    await expect(page.locator('#post-contour-view')).toBeVisible();

    const details = page.locator('details.group').filter({ hasText: 'Load custom VTK file' });
    const summary = details.locator('summary');
    const content = details.locator('.bg-white.border-t');

    // 2. Check initial state (Closed)
    // <details> without open attribute means closed.
    await expect(details).not.toHaveAttribute('open');
    await expect(content).toBeHidden();

    // 3. Click summary to expand
    await summary.click();

    // 4. Verify expanded
    await expect(details).toHaveAttribute('open', '');
    await expect(content).toBeVisible();

    // 5. Verify input focusable and visible
    const input = content.locator('input#vtkFileBrowser');
    await expect(input).toBeVisible();
    await input.focus();
    await expect(input).toBeFocused();

    // 6. Click summary to collapse
    await summary.click();

    // 7. Verify collapsed
    await expect(details).not.toHaveAttribute('open');
    await expect(content).toBeHidden();
  });
});
