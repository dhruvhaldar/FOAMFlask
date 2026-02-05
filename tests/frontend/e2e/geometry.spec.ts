
import { test, expect } from '@playwright/test';

test.describe('Geometry Management', () => {
  test.beforeEach(async ({ page }) => {
    // Mock successful startup
    await page.route('**/api/startup_status', async route => {
      await route.fulfill({ json: { status: 'completed', message: 'Ready' } });
    });

    // Mock initial data fetching
    await page.route('**/get_case_root', async route => {
        await route.fulfill({ json: { caseDir: '/tmp/FOAM_Run' } });
    });
    await page.route('**/get_docker_config', async route => {
        await route.fulfill({ json: { dockerImage: 'opencfd/openfoam-default', openfoamVersion: 'v2312' } });
    });
    await page.route('**/api/cases/list', async route => {
        await route.fulfill({ json: { cases: ['case1'] } });
    });

    // Default mock for geometry list to prevent 404s during initial load or tab switch
    await page.route(/.*\/api\/geometry\/list.*/, async route => {
        await route.fulfill({ json: { success: true, files: ['default.stl'] } });
    });

    await page.goto('/');
    await expect(page.locator('#startup-modal')).toBeHidden();

    // Select a case to ensure activeCase is set (required for geometry operations)
    await page.selectOption('#caseSelect', 'case1');

    // Switch to Geometry tab
    await page.click('#nav-geometry');
    await expect(page.locator('#page-geometry')).toBeVisible();
  });

  test('should display empty state when no geometry files exist', async ({ page }) => {
    // Override mock for empty list
    await page.unroute(/.*\/api\/geometry\/list.*/);
    await page.route(/.*\/api\/geometry\/list.*/, async route => {
      await route.fulfill({ json: { success: true, files: [] } });
    });

    // Trigger refresh
    await page.click('#refreshGeometryBtn');

    // Check for disabled option with "No geometry files found"
    const select = page.locator('#geometrySelect');
    await expect(select).toContainText('No geometry files found');

    // Verify the option is disabled
    const option = select.locator('option').first();
    await expect(option).toBeDisabled();
  });

  test('should upload a geometry file', async ({ page }) => {
    // Mock upload response
    await page.route('**/api/geometry/upload', async route => {
      await route.fulfill({ json: { success: true, message: 'File uploaded' } });
    });

    // Mock list refresh after upload (now containing the new file)
    await page.unroute(/.*\/api\/geometry\/list.*/);
    await page.route(/.*\/api\/geometry\/list.*/, async route => {
      await route.fulfill({ json: { success: true, files: ['test.stl'] } });
    });

    // Create a dummy file for upload
    const buffer = Buffer.from('solid test\nendsolid test');

    // Set file input
    await page.setInputFiles('#geometryUpload', {
      name: 'test.stl',
      mimeType: 'application/sla',
      buffer: buffer
    });

    // Click upload
    await page.click('#uploadGeometryBtn');

    // Check for success notification
    await expect(page.locator('.notification.bg-green-500')).toContainText('Geometry uploaded successfully');

    // Verify list is updated
    const select = page.locator('#geometrySelect');
    await expect(select).toContainText('test.stl');
  });

  test('should delete a geometry file', async ({ page }) => {
    // Initial state: one file exists (from default mock)
    // Refresh to make sure UI is in sync with default mock
    await page.click('#refreshGeometryBtn');
    await expect(page.locator('#geometrySelect')).toContainText('default.stl');
    await page.selectOption('#geometrySelect', 'default.stl');

    // Mock delete response
    await page.route('**/api/geometry/delete', async route => {
      await route.fulfill({ json: { success: true } });
    });

    // Mock list refresh after delete (empty)
    await page.unroute(/.*\/api\/geometry\/list.*/);
    await page.route(/.*\/api\/geometry\/list.*/, async route => {
      await route.fulfill({ json: { success: true, files: [] } });
    });

    // Handle confirm dialog
    page.on('dialog', dialog => dialog.accept());

    // Click delete
    await page.click('#deleteGeometryBtn');

    // Verify list is empty
    await expect(page.locator('#geometrySelect')).toContainText('No geometry files found');
  });

  test('should load interactive geometry view', async ({ page }) => {
    // Initial state: select default file
    await page.click('#refreshGeometryBtn');
    await page.selectOption('#geometrySelect', 'default.stl');

    // Mock view response
    await page.route('**/api/geometry/view', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<html><body>Interactive Geometry</body></html>'
      });
    });

    // Mock info response (called in parallel/sequence)
    await page.route('**/api/geometry/info', async route => {
      await route.fulfill({ json: { success: true, bounds: [0,1,0,1,0,1], center: [0.5,0.5,0.5], n_points: 100, n_cells: 100 } });
    });

    // Click View
    await page.click('#viewGeometryBtn');

    // Verify loading state (optional, might be too fast)
    // Verify iframe visibility and content
    const iframe = page.locator('#geometryInteractive');
    await expect(iframe).toBeVisible();

    // Verify placeholder is hidden
    await expect(page.locator('#geometryPlaceholder')).toBeHidden();

    // Verify info panel is shown
    await expect(page.locator('#geometryInfo')).toBeVisible();
  });
});
