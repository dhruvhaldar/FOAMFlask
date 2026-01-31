
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock dependencies
vi.mock('plotly.js', () => ({
  react: vi.fn(),
}));

describe('Geometry UX', () => {
  beforeEach(async () => {
    vi.resetModules();
    // Reset DOM
    document.body.innerHTML = `
      <div id="page-geometry" class="page">
         <label for="geometryUpload" id="geo-drop-zone">
            Drop Zone
            <input type="file" id="geometryUpload" />
         </label>
         <div id="geo-file-name" class="hidden"></div>
      </div>
    `;

    // Import the frontend code to trigger initialization/setup functions
    // Note: setupGeometryDragDrop is called in init() which runs on DOMContentLoaded or immediately if ready.
    // We need to force it to run or wait for it.
    // Since we are loading the module, and it checks document.readyState, it should attach.
    await import('../../../static/ts/foamflask_frontend.ts');

    // Manually trigger the init or wait for it if necessary.
    // The module adds event listener for DOMContentLoaded. In jsdom, if we are already loaded, we might miss it
    // unless we manually trigger it or if the code handles "complete" state.
    // The code does:
    // if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); } else { init(); }
    // JSDOM usually starts as 'loading' but depending on how vitest runs it might be 'complete'.
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('should show file name and remove button when file is selected', async () => {
    const input = document.getElementById('geometryUpload') as HTMLInputElement;
    const nameDisplay = document.getElementById('geo-file-name') as HTMLElement;

    // Simulate file selection
    const file = new File(['content'], 'test.stl', { type: 'model/stl' });
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: true
    });

    // Trigger change event
    input.dispatchEvent(new Event('change'));

    // Verify name is displayed
    expect(nameDisplay.classList.contains('hidden')).toBe(false);
    expect(nameDisplay.textContent).toContain('test.stl');

    // Check for remove button
    const removeBtn = nameDisplay.querySelector('button');
    expect(removeBtn).toBeTruthy();
    expect(removeBtn?.getAttribute('aria-label')).toBe('Remove file');
  });

  it('should clear selection when remove button is clicked', async () => {
    const input = document.getElementById('geometryUpload') as HTMLInputElement;
    const nameDisplay = document.getElementById('geo-file-name') as HTMLElement;

    // Simulate file selection first (assuming implementation exists)
    const file = new File(['content'], 'test.stl', { type: 'model/stl' });
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: true
    });

    // Trigger change event to run the logic
    input.dispatchEvent(new Event('change'));

    // Check if button exists
    const removeBtn = nameDisplay.querySelector('button');
    expect(removeBtn).toBeTruthy();

    if (removeBtn) {
        removeBtn.click();
        expect(input.value).toBe('');
        expect(nameDisplay.classList.contains('hidden')).toBe(true);
    }
  });
});
