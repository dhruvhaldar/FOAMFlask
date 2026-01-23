
import { test, expect } from '@playwright/test';

test.describe('Visualization Scroll Isolation', () => {
    test('iframe wheel events should not propagate to main window', async ({ page }) => {
        // 1. Navigate to the application
        await page.goto('http://127.0.0.1:5000/');

        // 2. Navigate to "Post" page
        // 2. Navigate to "Post" page
        // Using specific ID to avoid ambiguity (mobile vs desktop)
        const postNav = page.locator('#nav-post');
        if (await postNav.isVisible()) {
            await postNav.click();
        } else {
            // Fallback for mobile view if desktop nav is hidden
            await page.locator('#mobile-nav-post').click();
        }

        // 3. Select "Contour" visualization
        await page.click('#card-contour');

        // 4. Select a VTK file (Wait for list to populate)
        const select = page.locator('#vtkFileSelect');
        await expect(select).toBeVisible();

        // Give it a moment to fetch files if async
        await page.waitForTimeout(1000);

        const options = await select.locator('option').allInnerTexts();
        const vtkOption = options.find(opt => opt.toLowerCase().includes('.vtk'));

        if (!vtkOption) {
            test.skip(true, 'No VTK files available for testing');
            return;
        }

        console.log(`Selecting VTK File: ${vtkOption}`);
        await select.selectOption({ label: vtkOption });

        // 5. Load and Generate Contours
        await page.click('#loadContourVTKBtn');

        // Wait for "Load" to complete (optional check, but good practice)
        await page.waitForTimeout(500);

        console.log('Generating Contours...');
        await page.click('#generateContoursBtn');

        // 6. Wait for the iframe to appear
        const iframe = page.locator('#contourVisualizationFrame');
        await expect(iframe).toBeVisible({ timeout: 60000 }); // Give Trame time to start

        // 7. Verify Scroll Isolation
        // Ensure page is at top
        await page.evaluate(() => window.scrollTo(0, 0));
        const initialScrollY = await page.evaluate(() => window.scrollY);

        // Get iframe bounding box to hover over it
        const box = await iframe.boundingBox();
        expect(box).not.toBeNull();
        if (!box) return;

        // Move mouse to center of iframe
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);

        // Perform a significant scroll action
        console.log('Simulating mouse wheel...');
        await page.mouse.wheel(0, 1000);

        // Wait for potential scroll propagation
        await page.waitForTimeout(1000);

        // Check final scroll position
        const finalScrollY = await page.evaluate(() => window.scrollY);
        console.log(`Scroll Change: ${initialScrollY} -> ${finalScrollY}`);

        expect(finalScrollY).toBe(initialScrollY);
    });
});
