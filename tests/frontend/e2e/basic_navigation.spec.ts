
import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Mock successful startup
    await page.route('/api/startup_status', async route => {
      await route.fulfill({ json: { status: 'completed', message: 'Ready' } });
    });

    // Mock initial data fetching
    await page.route('/get_case_root', async route => {
        await route.fulfill({ json: { caseDir: '/tmp/FOAM_Run' } });
    });
    await page.route('/get_docker_config', async route => {
        await route.fulfill({ json: { dockerImage: 'opencfd/openfoam-default', openfoamVersion: 'v2312' } });
    });
    await page.route('/api/cases/list', async route => {
        await route.fulfill({ json: { cases: ['case1', 'case2'] } });
    });

    await page.goto('/');

    // Wait for startup modal to disappear
    await expect(page.locator('#startup-modal')).toBeHidden();
  });

  test('should switch tabs correctly', async ({ page }) => {
    // Check initial state (Setup tab active)
    await expect(page.locator('#nav-setup')).toHaveClass(/bg-blue-500/);
    await expect(page.locator('#page-setup')).toBeVisible();
    await expect(page.locator('#page-geometry')).toBeHidden();

    // Click Geometry tab
    await page.click('#nav-geometry');
    await expect(page.locator('#nav-geometry')).toHaveClass(/bg-blue-500/);
    await expect(page.locator('#nav-setup')).not.toHaveClass(/bg-blue-500/);
    await expect(page.locator('#page-geometry')).toBeVisible();
    await expect(page.locator('#page-setup')).toBeHidden();

    // Click Meshing tab
    await page.click('#nav-meshing');
    await expect(page.locator('#page-meshing')).toBeVisible();

    // Click Visualizer tab
    await page.click('#nav-visualizer');
    await expect(page.locator('#page-visualizer')).toBeVisible();

    // Click Run tab
    await page.click('#nav-run');
    await expect(page.locator('#page-run')).toBeVisible();

    // Click Plots tab
    await page.click('#nav-plots');
    await expect(page.locator('#plotsContainer')).toBeVisible();

    // Click Post tab
    await page.click('#nav-post');
    await expect(page.locator('#page-post')).toBeVisible();
  });
});
