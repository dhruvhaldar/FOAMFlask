
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock plotly.js to prevent errors during import
vi.mock('plotly.js', () => ({
  react: vi.fn(),
}));

describe('Geometry Feedback UX', () => {
  beforeEach(async () => {
    vi.resetModules();
    document.body.innerHTML = `
      <select id="geometrySelect">
        <option value="" disabled selected>No geometry files found</option>
      </select>
      <button id="viewGeometryBtn">View</button>
      <button id="deleteGeometryBtn">Delete</button>
      <div id="notificationContainer"></div>
      <template id="notification-template">
        <div class="notification">
            <span class="message-slot"></span>
        </div>
      </template>
      <div id="caseSelect"></div>
      <div id="activeCaseBadge"></div>
    `;

    // Import the frontend code
    await import('../../../static/ts/foamflask_frontend.ts');

    // Set active case via exposed global
    (window as any).selectCase('test_case');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('should show notification when viewing with no selection', async () => {
    const select = document.getElementById('geometrySelect') as HTMLSelectElement;

    // Ensure value is empty (matches our change in refreshGeometryList logic)
    select.value = "";

    await (window as any).loadGeometryView();

    // Verify notification was added to DOM
    const notifications = document.querySelectorAll('.notification .message-slot');
    const messages = Array.from(notifications).map(n => n.textContent);
    expect(messages).toContain("Please select a geometry file to view");

    // Verify focus and aria-invalid
    expect(document.activeElement).toBe(select);
    expect(select.getAttribute('aria-invalid')).toBe('true');
  });

  it('should show notification when deleting with no selection', async () => {
    const select = document.getElementById('geometrySelect') as HTMLSelectElement;

    select.value = "";

    await (window as any).deleteGeometry();

    const notifications = document.querySelectorAll('.notification .message-slot');
    const messages = Array.from(notifications).map(n => n.textContent);
    expect(messages).toContain("Please select a geometry file to delete");

    expect(document.activeElement).toBe(select);
    expect(select.getAttribute('aria-invalid')).toBe('true');
  });

  it('should remove aria-invalid on selection change', async () => {
    const select = document.getElementById('geometrySelect') as HTMLSelectElement;
    select.value = "";
    await (window as any).loadGeometryView();
    expect(select.getAttribute('aria-invalid')).toBe('true');

    // Simulate change
    select.dispatchEvent(new Event('change'));

    expect(select.hasAttribute('aria-invalid')).toBe(false);
  });
});
