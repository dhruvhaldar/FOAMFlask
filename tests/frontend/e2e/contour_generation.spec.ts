
import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
    // Mock API responses
    await page.route('/api/startup_status', async route => {
      await route.fulfill({ json: { status: 'completed', message: 'Ready' } });
    });

    await page.route('/get_case_root', async route => {
        await route.fulfill({ json: { caseDir: '/tmp/foamflask_test' } });
    });

    await page.route('/get_docker_config', async route => {
        await route.fulfill({ json: { dockerImage: 'test/image', openfoamVersion: 'v2206' } });
    });

    await page.route('/api/cases/list', async route => {
        await route.fulfill({ json: { cases: ['case1'] } });
    });

    await page.route('/api/available_meshes?tutorial=case1', async route => {
        await route.fulfill({ json: { meshes: [{ name: 'mesh.vtk', path: '/tmp/mesh.vtk' }] } });
    });

    // Mock load_mesh
    await page.route('/api/load_mesh', async route => {
        await route.fulfill({
            json: {
                success: true,
                n_points: 1000,
                n_cells: 1000,
                point_arrays: ['U_Magnitude', 'p'],
                field_stats: {
                    "U_Magnitude": { type: "scalar", min: 0, max: 10 }
                }
            }
        });
    });

    // Mock contour creation (The Core Change)
    await page.route('/api/contours/create', async route => {
        // Verify request is JSON
        const headers = route.request().headers();
        // Playwright normalizes headers to lowercase
        if (!headers['content-type']?.includes('application/json')) {
             await route.fulfill({ status: 400, body: 'Expected JSON content type' });
             return;
        }

        const postData = route.request().postDataJSON();
        // Basic validation
        if (postData.scalar_field === 'U_Magnitude') {
             await route.fulfill({
                 json: {
                     mode: 'iframe',
                     src: 'http://localhost:8000/index.html',
                     port: 8000
                 }
             });
        } else {
             await route.fulfill({ status: 500, json: { error: 'Invalid scalar field' } });
        }
    });

    // Start with a mock page
    await page.goto('/');

    // Select case using exposed function
    await page.evaluate(() => {
        (window as any).selectCase('case1');
    });

    // Wait for case to be selected (badge visible)
    await expect(page.locator('#activeCaseBadge')).toBeVisible();
    await expect(page.locator('#activeCaseBadge')).toHaveText('case1');
});

test('should generate contour and display iframe', async ({ page }) => {
    // 1. Navigate to Post Processing
    await page.click('#nav-post');
    await expect(page.locator('#post-landing-view')).toBeVisible();

    // 2. Click Contour Visualization (using ID)
    await page.click('#card-contour');
    await expect(page.locator('#post-contour-view')).toBeVisible();

    // 3. Select VTK file (should trigger load_mesh)
    // Wait for select to be populated (options are hidden by default, so wait for attachment)
    await page.waitForSelector('#vtkFileSelect option[value="/tmp/mesh.vtk"]', { state: 'attached' });
    await page.selectOption('#vtkFileSelect', '/tmp/mesh.vtk');

    // Click Load
    await page.click('#loadContourVTKBtn');

    // Wait for Info to appear (means load_mesh success)
    await expect(page.locator('#contourInfo')).toBeVisible();

    // 4. Click Generate Contours
    await page.click('#generateContoursBtn');

    // 5. Verify Iframe appears (handling the JSON response)
    const iframe = page.locator('#contourVisualizationFrame');
    await expect(iframe).toBeVisible();

    // Check src attribute
    const src = await iframe.getAttribute('src');
    expect(src).toContain('http://localhost:8000/index.html');
});
