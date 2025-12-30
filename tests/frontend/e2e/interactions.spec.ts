
import { test, expect } from '@playwright/test';

test.describe('Interactions', () => {
  test.beforeEach(async ({ page }) => {
    // Mock successful startup and base data
    await page.route('/api/startup_status', async route => {
      await route.fulfill({ json: { status: 'completed', message: 'Ready' } });
    });
    await page.route('/get_case_root', async route => {
        await route.fulfill({ json: { caseDir: '/tmp/FOAM_Run' } });
    });
    await page.route('/get_docker_config', async route => {
        await route.fulfill({ json: { dockerImage: 'opencfd/openfoam-default', openfoamVersion: 'v2312' } });
    });
    await page.route('/api/cases/list', async route => {
        await route.fulfill({ json: { cases: ['case1'] } });
    });

    await page.goto('/');
    await expect(page.locator('#startup-modal')).toBeHidden();
  });

  test('should load tutorial', async ({ page }) => {
    // Mock load_tutorial response
    await page.route('/load_tutorial', async route => {
      await route.fulfill({
        json: {
          success: true,
          caseDir: '/tmp/FOAM_Run/tut1',
          output: 'Tutorial loaded successfully'
        }
      });
    });

    // Mock case list refresh after loading
    await page.route('/api/cases/list', async route => {
        await route.fulfill({ json: { cases: ['case1', 'tut1'] } });
    });

    // Select a tutorial (assuming 'tut1' is in the mocked HTML or we can just set value)
    // Since the actual HTML might have different options, we can inject one for testing
    await page.evaluate(() => {
        const select = document.getElementById('tutorialSelect') as HTMLSelectElement;
        const opt = document.createElement('option');
        opt.value = 'tut1';
        opt.text = 'Tutorial 1';
        select.add(opt);
        select.value = 'tut1';
    });

    await page.click('#loadTutorialBtn');

    // Check for loading state
    await expect(page.locator('#loadTutorialBtn')).toBeDisabled();

    // Check for success notification
    await expect(page.locator('.notification.bg-green-500')).toContainText('Tutorial imported');

    // Check output log
    await expect(page.locator('#output')).toContainText('Tutorial loaded successfully');
  });

  test('should set case directory', async ({ page }) => {
    await page.route('/set_case', async route => {
      const payload = route.request().postDataJSON();
      await route.fulfill({
        json: {
          success: true,
          caseDir: payload.caseDir,
          output: 'Case dir set'
        }
      });
    });

    // Expand Advanced Configuration
    await page.click('summary');

    await page.fill('#caseDir', '/new/path');

    // Trigger setCase (assuming there's a button or blur, but likely the Set button)
    // The HTML has a "Set" button next to the input usually
    // We need to find the button that calls setCase.
    // Looking at the code: setCase(this) is called on the button.
    // We'll find it by text "Set Root" or similar.
    const setBtn = page.locator('button', { hasText: 'Set Root' }).first(); // Approximation

    // If we can't find it easily by text, we might need to rely on ID if available or structure.
    // The code uses `onclick="setCase(this)"`.
    // Let's assume the button exists. If not, we'll click the one near the input.
    // Alternatively, just eval it since we are testing the logic more than the layout here,
    // BUT this is E2E, so we should click.

    // Let's use a locator based on the onclick attribute if possible, or parent.
    await page.locator('button[onclick*="setCase"]').click();

    await expect(page.locator('.notification.bg-blue-500')).toContainText('Case directory set');
  });

  test('should run command', async ({ page }) => {
    await page.route('/api/meshing/run', async route => {
       // Mock streaming response with delay
       await new Promise(resolve => setTimeout(resolve, 2000));
       await route.fulfill({
           json: { success: true, output: 'Meshing completed' }
       });
    });

    // Select a case via UI
    await page.selectOption('#caseSelect', 'case1');

    // Let's go to Meshing tab
    await page.click('#nav-meshing');

    // Find a button that runs a command, e.g., BlockMesh
    const runBtn = page.locator('button', { hasText: 'Run blockMesh' });

    await runBtn.click();

    // Check for success
    await expect(page.locator('.notification.bg-green-500')).toContainText('Meshing completed successfully');
  });

  test('should toggle plots', async ({ page }) => {
    await page.click('#nav-plots');

    // Initially hidden or visible? Code says `plotsVisible = true` initially but container hidden until tab switch?
    // switchPage('plots') removes hidden from plotsContainer.

    const container = page.locator('#plotsContainer');
    const toggleBtn = page.locator('#togglePlotsBtn');

    await expect(container).toBeVisible();
    await expect(toggleBtn).toHaveText('Hide Plots');

    await toggleBtn.click();
    await expect(container).toBeHidden();
    await expect(toggleBtn).toHaveText('Show Plots');

    await toggleBtn.click();
    await expect(container).toBeVisible();
  });
});
