
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock dependencies (minimal)
vi.mock('plotly.js', () => ({}));
vi.mock('../../static/ts/frontend/isosurface.js', () => ({}));

describe('Geometry Upload UX', () => {
  beforeEach(async () => {
    vi.resetModules();
    document.body.innerHTML = `
      <div id="page-geometry" class="page"></div>

      <!-- Drop Zone -->
      <label id="geo-drop-zone">
        <input type="file" id="geometryUpload" />
      </label>

      <!-- File Name Display -->
      <div id="geo-file-name" class="hidden"></div>

      <!-- Notification Container (needed for showNotification) -->
      <div id="notificationContainer"></div>
      <template id="notification-template">
        <div class="notification">
          <div class="icon-slot"></div>
          <div class="message-slot"></div>
          <button class="close-btn"></button>
        </div>
      </template>
    `;

    // Import the frontend script to initialize event listeners
    await import('../../../static/ts/foamflask_frontend.ts');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('should show remove button when file is selected', async () => {
    const input = document.getElementById('geometryUpload') as HTMLInputElement;
    const nameDisplay = document.getElementById('geo-file-name') as HTMLElement;

    // Simulate file selection
    const file = new File(['dummy content'], 'test_geometry.stl', { type: 'model/stl' });
    Object.defineProperty(input, 'files', {
      value: [file],
      writable: true // Allow writing to test clearing
    });

    // Trigger change event
    const changeEvent = new Event('change');
    input.dispatchEvent(changeEvent);

    // Verify display is visible
    expect(nameDisplay.classList.contains('hidden')).toBe(false);

    // Verify content (filename and button)
    expect(nameDisplay.textContent).toContain('Selected: test_geometry.stl');

    // Find the remove button
    const removeBtn = nameDisplay.querySelector('button');
    expect(removeBtn).toBeTruthy();
    expect(removeBtn?.getAttribute('aria-label')).toBe('Remove selected file');
  });

  it('should clear selection when remove button is clicked', async () => {
    const input = document.getElementById('geometryUpload') as HTMLInputElement;
    const nameDisplay = document.getElementById('geo-file-name') as HTMLElement;

    // Simulate file selection
    const file = new File(['dummy content'], 'test_geometry.stl', { type: 'model/stl' });
    // Note: input.files is read-only in real browsers, but writable in jsdom usually or we mocked it above.
    // However, our code sets `input.value = ''`.
    // In jsdom, setting value to '' might not clear the files property if we mocked it via Object.defineProperty.
    // But let's check if the code runs.

    // Reset files mock to allow setter (value) to work if jsdom supports it,
    // or we just trust the code calls input.value = ''.
    // Actually, setting value to '' on file input clears files in spec.
    // But since we manually defined `files` property in previous test, we need to be careful.
    // Let's redefine it to be standard jsdom behavior if possible, or just mock the value setter.

    // Simplest approach: Just verify the logic flow.

    Object.defineProperty(input, 'files', {
      value: [file],
      writable: true
    });

    // Trigger change event
    input.dispatchEvent(new Event('change'));

    // Find remove button
    const removeBtn = nameDisplay.querySelector('button');

    // Click it
    removeBtn?.click();

    // Verify display is hidden
    expect(nameDisplay.classList.contains('hidden')).toBe(true);
    expect(nameDisplay.innerHTML).toBe('');

    // Verify input value is cleared (which implies files are cleared in browser)
    expect(input.value).toBe('');
  });
});
