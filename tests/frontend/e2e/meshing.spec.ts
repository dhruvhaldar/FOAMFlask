
import { test, expect } from '@playwright/test';

test.describe('Meshing Tab', () => {
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

    // Default geometry list mock
    await page.route(/.*\/api\/geometry\/list.*/, async route => {
        await route.fulfill({ json: { success: true, files: ['test.stl'] } });
    });

    await page.goto('/');
    await expect(page.locator('#startup-modal')).toBeHidden();

    // Select case
    await page.selectOption('#caseSelect', 'case1');

    // Go to Meshing
    await page.click('#nav-meshing');
    await expect(page.locator('#page-meshing')).toBeVisible();
  });

  test('should generate blockMeshDict', async ({ page }) => {
    // Check if section is visible, if not toggle it
    const section = page.locator('#blockMeshSection');
    if (!await section.isVisible()) {
        await page.click('#blockMeshSectionToggle');
    }

    // Mock API
    await page.route('**/api/meshing/blockMesh/config', async route => {
      await route.fulfill({ json: { success: true } });
    });

    // Ensure visible
    await page.locator('#bmCells').scrollIntoViewIfNeeded();

    await page.fill('#bmCells', '10 10 10');

    await page.click('#genBlockMeshBtn');

    await expect(page.locator('.notification.bg-green-500')).toContainText('Generated');
  });

  test('should run blockMesh', async ({ page }) => {
    // Ensure visible
    const runBtn = page.locator('#runBlockMeshBtn');
    await runBtn.scrollIntoViewIfNeeded();

    await page.route('**/api/meshing/run', async route => {
        await route.fulfill({ json: { success: true, output: 'blockMesh output' } });
    });

    await page.click('#runBlockMeshBtn');

    await expect(page.locator('.notification.bg-green-500')).toContainText('Meshing completed successfully');
    await expect(page.locator('#meshingOutput')).toContainText('blockMesh output');
  });

  test('should generate snappyHexMeshDict', async ({ page }) => {
     // Mock API
     await page.route('**/api/meshing/snappyHexMesh/config', async route => {
        await route.fulfill({ json: { success: true } });
     });

     // Check if select is populated
     const select = page.locator('#shmObjectList');
     await expect(select).toBeVisible();

     // Wait for option to appear
     await expect(select).not.toBeEmpty();

     // Select the option explicitly
     await select.selectOption({ label: 'test.stl' });

     // Trigger change event
     await select.dispatchEvent('change');

     // Debugging: check if value is set
     const value = await select.inputValue();
     if (!value) {
         // Force set it via evaluate if selectOption fails in this mock context (unlikely but possible)
         await page.evaluate(() => {
             const sel = document.getElementById('shmObjectList') as HTMLSelectElement;
             if (sel && sel.options.length > 0) {
                 sel.value = sel.options[0].value;
             }
         });
     }

     await page.click('#genSnappyHexMeshBtn');

     await expect(page.locator('.notification.bg-green-500')).toContainText('success', { ignoreCase: true });
  });

  test('should run snappyHexMesh', async ({ page }) => {
    await page.route('**/api/meshing/run', async route => {
        await route.fulfill({ json: { success: true, output: 'snappy output' } });
    });

    await page.click('#runSnappyHexMeshBtn');

    await expect(page.locator('.notification.bg-green-500')).toContainText('Meshing completed successfully');
  });
});
