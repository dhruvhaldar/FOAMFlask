
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock dependencies
vi.mock('plotly.js', () => ({
  react: vi.fn(),
}));

describe('Palette Geometry Upload Validation', () => {
  beforeEach(async () => {
    vi.resetModules();
    document.body.innerHTML = `
      <div id="page-geometry">
         <input type="file" id="geometryUpload" />
         <button id="uploadGeometryBtn">Upload</button>
      </div>
      <div id="notificationContainer"></div>
      <template id="notification-template">
        <div class="notification">
            <span class="icon-slot"></span>
            <span class="message-slot"></span>
            <button class="close-btn"></button>
            <div class="progress-bar"></div>
        </div>
      </template>
    `;

    // Import main file to attach functions to window
    await import('../../../static/ts/foamflask_frontend.ts');

    // Mock active case
    (window as any).selectCase('test_case');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  const getNotificationText = () => {
    const notifications = document.querySelectorAll('.notification .message-slot');
    return Array.from(notifications).map(n => n.textContent);
  };

  it('should reject files larger than 500MB', async () => {
    const input = document.getElementById('geometryUpload') as HTMLInputElement;
    const { uploadGeometry } = window as any;

    // Create a large file mock (size in bytes)
    const largeFile = {
      name: 'large.stl',
      size: 500 * 1024 * 1024 + 1, // 500MB + 1 byte
      type: 'model/stl'
    };

    Object.defineProperty(input, 'files', {
      value: [largeFile],
      writable: true
    });

    await uploadGeometry();

    const messages = getNotificationText();
    expect(messages.some(msg => msg?.includes('File too large'))).toBe(true);
  });

  it('should reject invalid file extensions', async () => {
    const input = document.getElementById('geometryUpload') as HTMLInputElement;
    const { uploadGeometry } = window as any;

    const invalidFile = {
      name: 'test.txt',
      size: 1024,
      type: 'text/plain'
    };

    Object.defineProperty(input, 'files', {
      value: [invalidFile],
      writable: true
    });

    await uploadGeometry();

    const messages = getNotificationText();
    expect(messages.some(msg => msg?.includes('Invalid file type'))).toBe(true);
  });

  it('should allow valid files', async () => {
    const input = document.getElementById('geometryUpload') as HTMLInputElement;
    const { uploadGeometry } = window as any;

    // Mock fetch for successful upload
    global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true })
    });

    const validFile = {
      name: 'valid.stl',
      size: 1024,
      type: 'model/stl'
    };

    Object.defineProperty(input, 'files', {
      value: [validFile],
      writable: true
    });

    await uploadGeometry();

    const messages = getNotificationText();
    expect(messages.some(msg => msg?.includes('Geometry uploaded successfully'))).toBe(true);
  });
});
