import { test, expect } from '@playwright/test';

test('Post Processing Pipeline Screenshot', async ({ page }) => {
  // Go to page
  await page.goto('/');

  // Manually switch to Post page and setup pipeline state
  await page.evaluate(() => {
    // Switch page
    document.querySelectorAll('.page').forEach(el => el.classList.add('hidden'));
    document.getElementById('page-post').classList.remove('hidden');

    // Add a contour step to visualize pipeline
    const { switchPostView } = window as any;
    if (switchPostView) {
        switchPostView('contour');
    }
  });

  // Wait for animation/render
  await page.waitForTimeout(500);

  // Take screenshot of full page
  await page.screenshot({ path: 'Screenshots/post_processing_full.png', fullPage: true });

  // Take screenshot of pipeline element
  const pipeline = page.locator('#post-pipeline-view');
  if (await pipeline.isVisible()) {
      await pipeline.screenshot({ path: 'Screenshots/pipeline_tree.png' });
  }
});
