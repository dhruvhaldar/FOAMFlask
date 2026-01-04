
import { test, expect } from '@playwright/test';

test.describe('Visualizer Tab', () => {
  test.beforeEach(async ({ page }) => {
    // Mock successful startup and base data
    await page.route('**/api/startup_status', async route => {
      await route.fulfill({ json: { status: 'completed', message: 'Ready' } });
    });
    await page.route('**/get_case_root', async route => {
        await route.fulfill({ json: { caseDir: '/tmp/FOAM_Run' } });
    });
    await page.route('**/get_docker_config', async route => {
        await route.fulfill({ json: { dockerImage: 'opencfd/openfoam-default', openfoamVersion: 'v2312' } });
    });
    await page.route('**/api/cases/list', async route => {
        await route.fulfill({ json: { cases: ['case1'] } });
    });

    // Default mesh list
    await page.route('**/api/available_meshes*', async route => {
        await route.fulfill({ json: { meshes: [{ path: '/tmp/mesh.vtk', name: 'mesh.vtk' }] } });
    });

    await page.goto('/');
    await expect(page.locator('#startup-modal')).toBeHidden();

    // Select case
    await page.selectOption('#caseSelect', 'case1');

    // Go to Visualizer
    await page.click('#nav-visualizer');
    await expect(page.locator('#page-visualizer')).toBeVisible();
  });

  test('should run foamToVTK', async ({ page }) => {
    await page.route('**/run_foamtovtk', async route => {
        await route.fulfill({ body: 'foamToVTK output...' });
        // Note: frontend expects streaming body, simple body works for fetch mock usually
    });

    // Mock refreshing list after run
    await page.route('**/api/available_meshes*', async route => {
        await route.fulfill({ json: { meshes: [{ path: '/tmp/new_mesh.vtk', name: 'new_mesh.vtk' }] } });
    });

    await page.click('#runFoamToVTKBtn');

    await expect(page.locator('.notification.bg-green-500')).toContainText('foamToVTK completed');
  });

  test('should refresh mesh list', async ({ page }) => {
    await page.click('#refreshMeshListBtn');
    await expect(page.locator('.notification.bg-green-500')).toContainText('Mesh list refreshed');

    const select = page.locator('#meshSelect');
    await expect(select).toContainText('mesh.vtk');
  });

  test('should load mesh', async ({ page }) => {
    await page.route('**/api/mesh_screenshot', async route => {
        await route.fulfill({ json: { success: true, image: 'base64image' } });
    });

    await page.selectOption('#meshSelect', { index: 1 }); // Index 0 is default option
    await page.click('#loadMeshBtn');

    await expect(page.locator('#meshImage')).toBeVisible();
    await expect(page.locator('#meshPlaceholder')).toBeHidden();
    await expect(page.locator('#meshControls')).toBeVisible();
  });

  test('should toggle interactive mode', async ({ page }) => {
    // Load mesh first
    await page.route('**/api/mesh_screenshot', async route => {
        await route.fulfill({ json: { success: true, image: 'base64image' } });
    });
    await page.selectOption('#meshSelect', { index: 1 });
    await page.click('#loadMeshBtn');

    // Mock interactive view
    await page.route('**/api/mesh_interactive', async route => {
        await route.fulfill({ body: '<html>Interactive View</html>' });
    });

    await page.click('#toggleInteractiveBtn');

    await expect(page.locator('#meshInteractive')).toBeVisible();
    await expect(page.locator('#toggleInteractiveBtn')).toHaveText('Static Mode');

    // Toggle back
    await page.click('#toggleInteractiveBtn');
    await expect(page.locator('#meshInteractive')).toBeHidden();
    await expect(page.locator('#toggleInteractiveBtn')).toHaveText('Interactive Mode');
  });

  test('should update view', async ({ page }) => {
    // Load mesh first
    await page.route('**/api/mesh_screenshot', async route => {
        await route.fulfill({ json: { success: true, image: 'base64image' } });
    });
    await page.selectOption('#meshSelect', { index: 1 });
    await page.click('#loadMeshBtn');

    // Change parameters
    await page.uncheck('#showEdges');
    await page.selectOption('#meshColor', 'red');

    // Mock update
    let capturedRequest;
    await page.route('**/api/mesh_screenshot', async route => {
        capturedRequest = route.request().postDataJSON();
        await route.fulfill({ json: { success: true, image: 'updated_image' } });
    });

    await page.click('#updateViewBtn');

    // Verify parameters sent
    expect(capturedRequest.show_edges).toBe(false);
    expect(capturedRequest.color).toBe('red');
  });
});
