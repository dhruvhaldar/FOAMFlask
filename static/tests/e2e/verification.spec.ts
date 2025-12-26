import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

test.describe('Frontend Verification', () => {
  test('should load static HTML and verify accessibility and visibility', async ({ page }) => {
    // Construct file URL for the local HTML file
    const htmlPath = path.resolve(process.cwd(), 'static/html/foamflask_frontend.html');

    // Ensure file exists
    if (!fs.existsSync(htmlPath)) {
      throw new Error(`HTML file not found at ${htmlPath}`);
    }

    const fileUrl = `file://${htmlPath}`;
    console.log(`Loading ${fileUrl}`);

    await page.goto(fileUrl);

    // 1. Verify 'Import Tutorial' loading state components
    const importBtn = page.getByRole('button', { name: 'Import Tutorial' });
    await expect(importBtn).toBeVisible();

    // 2. Verify accessibility improvements

    // -- GEOMETRY PAGE --
    // Manually unhide the geometry page via DOM manipulation
    await page.evaluate(() => {
        const el = document.getElementById('page-geometry');
        if (el) el.classList.remove('hidden');
    });

    // Check 'Available Geometries' label association
    const geoLabel = page.getByText('Available Geometries');
    await expect(geoLabel).toBeVisible();

    // Check if the label is associated with the select (validates 'for' attribute)
    const geoSelect = page.getByLabel('Available Geometries');
    await expect(geoSelect).toBeVisible();
    await expect(geoSelect).toHaveAttribute('id', 'geometrySelect');
    console.log('Geometry page accessibility verified.');

    // -- VISUALIZER PAGE --
    // Manually unhide the visualizer page
    await page.evaluate(() => {
        const el = document.getElementById('page-visualizer');
        if (el) el.classList.remove('hidden');
    });

    // Verify meshSelect has aria-label
    const meshSelect = page.locator('#meshSelect');
    await expect(meshSelect).toHaveAttribute('aria-label', 'Select Mesh File');
    console.log('Visualizer page accessibility verified.');

    // -- POST PAGE --
    // Manually unhide the post page
    await page.evaluate(() => {
        const el = document.getElementById('page-post');
        if (el) el.classList.remove('hidden');
    });

    // Verify VTK File Select label association
    const vtkSelect = page.getByLabel('Select VTK File');
    await expect(vtkSelect).toBeVisible();
    await expect(vtkSelect).toHaveAttribute('id', 'vtkFileSelect');

    // Verify Scalar Field label association
    // Using exact=true to avoid partial matches
    const scalarSelect = page.getByLabel('Scalar Field', { exact: true });
    await expect(scalarSelect).toBeVisible();
    await expect(scalarSelect).toHaveAttribute('id', 'scalarField');

    // Verify Color Map label association
    const colorMapSelect = page.getByLabel('Color Map');
    await expect(colorMapSelect).toBeVisible();
    await expect(colorMapSelect).toHaveAttribute('id', 'colorMap');
    console.log('Post page accessibility verified.');
  });
});
