
import { test, expect } from '@playwright/test';

test.describe('Setup Tab', () => {
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

    await page.goto('/');
    await expect(page.locator('#startup-modal')).toBeHidden();
    await expect(page.locator('#page-setup')).toBeVisible();
  });

  test('should set case root directory', async ({ page }) => {
    await page.route('**/set_case', async route => {
        const payload = route.request().postDataJSON();
        await route.fulfill({ json: { success: true, caseDir: payload.caseDir, output: 'INFO: Root set' } });
    });

    // Open Advanced Config
    await page.click('summary');

    await page.fill('#caseDir', '/new/path');
    await page.click('#setRootBtn');

    await expect(page.locator('.notification.bg-blue-500')).toContainText('Case directory set');
    await expect(page.locator('#caseDir')).toHaveValue('/new/path');
  });

  test('should set docker configuration', async ({ page }) => {
    await page.route('**/set_docker_config', async route => {
        const payload = route.request().postDataJSON();
        await route.fulfill({
            json: {
                success: true,
                dockerImage: payload.dockerImage,
                openfoamVersion: payload.openfoamVersion
            }
        });
    });

    // Open Advanced Config
    await page.click('summary');

    await page.fill('#dockerImage', 'my/image');
    await page.fill('#openfoamVersion', 'v2406');
    await page.click('#setDockerConfigBtn');

    await expect(page.locator('.notification.bg-green-500')).toContainText('Docker config updated');
  });

  test('should create a new case', async ({ page }) => {
    await page.route('**/api/case/create', async route => {
        await route.fulfill({ json: { success: true, message: 'Case created' } });
    });

    // Mock list refresh after creation
    await page.route('**/api/cases/list', async route => {
        await route.fulfill({ json: { cases: ['case1', 'newCase'] } });
    });

    await page.fill('#newCaseName', 'newCase');
    await page.click('#createCaseBtn');

    await expect(page.locator('.notification.bg-green-500')).toContainText('Case created');

    // Verify it auto-selects the new case
    await expect(page.locator('#caseSelect')).toHaveValue('newCase');
  });

  test('should import a tutorial', async ({ page }) => {
    await page.route('**/load_tutorial', async route => {
        await route.fulfill({ json: { success: true, caseDir: '/tmp/FOAM_Run/tut1', output: 'Done' } });
    });

    // Mock list refresh
    await page.route('**/api/cases/list', async route => {
        await route.fulfill({ json: { cases: ['case1', 'tut1'] } });
    });

    // Select tutorial (mocked in index)
    await page.selectOption('#tutorialSelect', 'tut1');
    await page.click('#loadTutorialBtn');

    await expect(page.locator('.notification.bg-green-500')).toContainText('Tutorial imported');

    // Verify it auto-selects (logic extracts name from path)
    await expect(page.locator('#caseSelect')).toHaveValue('tut1');
  });

  test('should refresh case list', async ({ page }) => {
    // Override mock to return more cases
    await page.route('**/api/cases/list', async route => {
        await route.fulfill({ json: { cases: ['case1', 'case2', 'case3'] } });
    });

    await page.click('#refreshCaseListBtn');

    await expect(page.locator('.notification.bg-green-500')).toContainText('Case list refreshed');
    const options = await page.locator('#caseSelect option').allInnerTexts();
    expect(options).toContain('case1');
    expect(options).toContain('case2');
    expect(options).toContain('case3');
  });
});
